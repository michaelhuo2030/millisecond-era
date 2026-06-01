# 知识生命体 · 解剖与生命循环

```mermaid
graph LR
  DNA["🧬 DNA<br/>法则库 (L0…)"]:::o
  MET["♻️ 新陈代谢<br/>kit 消化实验"]:::o
  IMM["🛡️ 免疫<br/>gates 拒弱证据"]:::o
  NER["🕸️ 神经<br/>法则↔证据图谱"]:::o
  SC["🔁 自纠<br/>reflect 标矛盾"]:::o
  SEN["👁️ 感官<br/>recall 行动前感知"]:::o
  EXP["实验/session"] --> IMM
  IMM -->|过审/降级/VOID| MET
  MET --> NER
  NER --> SC
  SC --> SEN
  SEN -->|浮现已知| EXP
  DNA -.挂载.- NER
  classDef o fill:#efe,stroke:#272,stroke-width:2px
```
