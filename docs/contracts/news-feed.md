# 新闻契约 · Python 采集 → Java 拉取

> variant-migration 阶段 1 建立。Python 采集服务与 yudao `module-variant` 之间**唯一**的数据缝。
> 方向：**Java 拉（pull）**，Python 只提供只读端点。两边库不同（Python=Postgres，Java=MySQL），不共享表。

## 端点

```
GET /api/contract/news?since=<ISO8601>&limit=<1..500>
Header: X-Service-Token: <SERVICE_TOKEN>
```

- **鉴权**：服务令牌，非用户 JWT。请求头 `X-Service-Token` 必须等于服务端 `SERVICE_TOKEN`。
  服务端未配置 `SERVICE_TOKEN` → `503`；令牌缺失/不符 → `401`。
- **since**：只返回 `ingestedAt` **严格晚于**该时刻的新闻。不传 = 从头全量。
- **limit**：单页条数，默认 100，上限 500。

## 出参

```jsonc
{
  "items": [
    {
      "id": "n_ab12cd34ef56",        // URL 指纹，稳定去重键；Java 侧按此幂等 upsert
      "headline": "SAHM-X rilis laporan kuartal",
      "source": "财经源A",
      "url": "https://ex.com/a/1",
      "publishedAt": "2025-05-25T10:24:00+07:00",  // 原发布时间，可回填历史、不单调
      "summary": "已清洗的原文摘要（≤600字，已过抗注入 sanitize）",
      "ingestedAt": "2026-07-16T08:30:12.345+00:00" // 入库时间，机器游标
    }
  ],
  "nextSince": "2026-07-16T08:30:12.345+00:00"      // 本页最后一条 ingestedAt；无更多为 null
}
```

## 增量拉取协议（Java 侧）

1. 存一个 watermark（初始为空/很早的时间）。
2. `GET /api/contract/news?since=<watermark>&limit=100`。
3. 对每条按 `id` **幂等 upsert** 进 MySQL；富化（相关性/摘要/keyFacts/tickers/heat/label）用 module-ai 自行计算。
4. 若返回非空，把 watermark 更新为 `nextSince`，回到步骤 2，直到某次返回空。

**为何游标用 `ingestedAt` 而非 `publishedAt`**：发布时间可被回填成历史时刻、非单调，用它做游标会漏掉「晚抓到的旧文」。入库时间单调递增，是可靠的增量水位线。排序为 `(ingestedAt, id)` 双键，同一时刻多条也顺序稳定。

## 边界与约定

- **富化不在契约内**：采集器只给原始事实 + `summary`。相关性判定、摘要、结构化事实是 Java 的活。
- **id 稳定**：同一篇文章（剥离 utm/fbclid 等追踪参数后）URL 指纹一致，重复抓取不会产生新 id。
- **删除不通知**：契约只增量给「新增」。采集器不删新闻；Java 侧无需处理删除。
- 契约变更（加字段/改语义）需同步改本文件与 `backend/app/routers/feed.py`、`schemas.py` 的 `NewsFeedItem`。
