#!/usr/bin/env python3
"""T_MM2 — does TRAINING-TIME ternary recover what post-hoc ternary destroys (the 0% baseline)?
Small CNN on CIFAR-10, three ways: fp32 / trained-ternary (QAT, BitNet-style STE) / post-hoc ternary.
The BitNet thesis says trained-ternary is near-lossless; T_MM1 showed post-hoc = 0%. This tests it directly.
main mac, MPS. torch 2.12."""
import torch, torchvision, time, json, os
import torch.nn as nn, torch.nn.functional as F
dev = "mps" if torch.backends.mps.is_available() else "cpu"

def ternarize(w):
    a = w.abs().mean()
    t = torch.zeros_like(w); t[w > 0.7*a] = a; t[w < -0.7*a] = -a
    return t
class TernConv(nn.Conv2d):
    def forward(self, x):
        w = self.weight + (ternarize(self.weight) - self.weight).detach()  # STE: forward ternary, backward identity
        return self._conv_forward(x, w, self.bias)
class TernLinear(nn.Linear):
    def forward(self, x):
        w = self.weight + (ternarize(self.weight) - self.weight).detach()
        return F.linear(x, w, self.bias)

def make_net(tern=False):
    C = TernConv if tern else nn.Conv2d
    L = TernLinear if tern else nn.Linear
    return nn.Sequential(
        C(3,32,3,padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),
        C(32,64,3,padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
        C(64,128,3,padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.AdaptiveAvgPool2d(1),
        nn.Flatten(), L(128,10))

def loaders(bs=256):
    tf = torchvision.transforms.ToTensor()
    root = os.path.expanduser("~/hdc_scratch/cifar")
    tr = torchvision.datasets.CIFAR10(root, train=True, download=True, transform=tf)
    te = torchvision.datasets.CIFAR10(root, train=False, download=True, transform=tf)
    return (torch.utils.data.DataLoader(tr,bs,shuffle=True),
            torch.utils.data.DataLoader(te,bs))

def train_eval(net, tr, te, epochs):
    net.to(dev); opt = torch.optim.Adam(net.parameters(), 1e-3)
    for ep in range(epochs):
        net.train()
        for x,y in tr:
            x,y=x.to(dev),y.to(dev); opt.zero_grad()
            F.cross_entropy(net(x),y).backward(); opt.step()
    net.eval(); correct=tot=0
    with torch.no_grad():
        for x,y in te:
            x,y=x.to(dev),y.to(dev)
            correct += (net(x).argmax(1)==y).sum().item(); tot += y.numel()
    return correct/tot

def main():
    import sys; epochs = 2 if "--poc" in sys.argv else 8
    tr,te = loaders()
    t0=time.time(); res={}
    # 1. fp32
    net = make_net(False); res["fp32"] = train_eval(net, tr, te, epochs)
    # 3. post-hoc ternary: take fp32 weights, hard-ternarize, eval (no retrain)
    ph = make_net(True); ph.load_state_dict(net.state_dict()); ph.to(dev).eval()
    c=t=0
    with torch.no_grad():
        for x,y in te:
            x,y=x.to(dev),y.to(dev); c+=(ph(x).argmax(1)==y).sum().item(); t+=y.numel()
    res["post_hoc_ternary"] = c/t
    # 2. trained ternary (QAT from scratch)
    netT = make_net(True); res["trained_ternary"] = train_eval(netT, tr, te, epochs)
    res["epochs"]=epochs; res["minutes"]=round((time.time()-t0)/60,1)
    print(json.dumps(res, indent=2))
    print(f"\n  fp32={res['fp32']*100:.1f}%  trained-ternary={res['trained_ternary']*100:.1f}%  "
          f"post-hoc-ternary={res['post_hoc_ternary']*100:.1f}%  (chance=10%)")
    print(f"  >>> trained-ternary recovers {res['trained_ternary']*100:.1f}% vs post-hoc {res['post_hoc_ternary']*100:.1f}% "
          f"-> 训练时三值{'救回来了' if res['trained_ternary']>res['post_hoc_ternary']+0.1 else '没救回'}")
    json.dump(res, open(os.path.expanduser("~/hdc_scratch/t_mm2_result.json"),"w"), indent=2)

if __name__=="__main__":
    os.makedirs(os.path.expanduser("~/hdc_scratch/cifar"),exist_ok=True); main()
