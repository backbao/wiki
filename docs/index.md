---
layout: home
---

# AI Chat Docs

接口文档、在线调试和版本变更清单。

## 入口

- [API 接口总览](/api/)
- [接口变更清单](/api/changelog)
- [在线调试](/api/playground)

## 规则

- 以 `docs/.vitepress/openapi-spec.json` 作为当前版本基线
- 以 `docs/api/changelog.md` 作为每次接口变化的公开记录
- CI 必须在拉取请求中校验文档生成结果
