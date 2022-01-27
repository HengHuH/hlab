# HLab

Heng's Laboratory.

## 构建

**平台**

| 平台 | 编译器 | target cpu |
| -- | -- | -- |
| Windows | msvc | x64,x86 |

**依赖**

GN (1939), Ninja 1.10.0

**build**

```
gn gen -C out
ninja -C out
```