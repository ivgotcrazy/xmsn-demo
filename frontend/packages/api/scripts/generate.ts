/**
 * 契约派生代码生成器（架构 5.4 / 5.5，ADR-10/11）。
 *
 * 从 openapi/openapi.json（契约快照，后端唯一真相源）生成：
 *  - src/types.ts        全部 schema 的 TS 类型（生成物，只读勿手改）
 *  - src/client.ts       全部接口的 API 客户端函数（生成物，只读勿手改）
 *  - src/msw/handlers.ts MSW 拦截 handlers（生成物，契约派生；数据由 mockData 提供）
 *
 * 运行：pnpm --filter @xmsn/api generate（tsx scripts/generate.ts）
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname, "..")
const outDir = join(root, "src")

const spec = JSON.parse(readFileSync(join(root, "openapi", "openapi.json"), "utf-8"))
const schemas: Record<string, any> = spec.components?.schemas ?? {}
const paths: Record<string, any> = spec.paths ?? {}

// ---------- helpers ----------
const refName = (ref: string): string => ref.replace("#/components/schemas/", "")
const httpMethods = ["get", "post", "put", "patch", "delete"] as const
const camel = (s: string): string => s.replace(/[_-]+(\w)/g, (_m, c: string) => c.toUpperCase())

function tsType(schema: any, indent = ""): string {
  if (!schema) return "unknown"
  if (schema.$ref) return refName(schema.$ref)
  if (schema.allOf) {
    return schema.allOf.map((s: any) => tsType(s, indent)).join(" & ")
  }
  if (schema.anyOf) {
    const parts = schema.anyOf.map((s: any) => tsType(s, indent))
    return parts.length > 1 ? `(${parts.join(" | ")})` : parts[0]
  }
  if (schema.oneOf) {
    const parts = schema.oneOf.map((s: any) => tsType(s, indent))
    return parts.length > 1 ? `(${parts.join(" | ")})` : parts[0]
  }
  if (schema.type === "array") return `${tsType(schema.items, indent)}[]`
  if (schema.type === "object" || schema.properties || schema.additionalProperties) {
    const props = schema.properties ?? {}
    const lines = Object.entries(props).map(([k, v]: [string, any]) => {
      const required = schema.required?.includes(k)
      const opt = required ? "" : "?"
      return `${indent}  ${k}${opt}: ${tsType(v, indent + "  ")};`
    })
    if (schema.additionalProperties && schema.additionalProperties !== true) {
      lines.push(`${indent}  [key: string]: ${tsType(schema.additionalProperties, indent)};`)
    }
    return lines.length ? `{\n${lines.join("\n")}\n${indent}}` : "Record<string, unknown>"
  }
  switch (schema.type) {
    case "string":
      return schema.enum ? schema.enum.map((e: unknown) => JSON.stringify(e)).join(" | ") : "string"
    case "integer":
    case "number":
      return "number"
    case "boolean":
      return "boolean"
    case "null":
      return "null"
    default:
      return "unknown"
  }
}

// ---------- 1) types.ts ----------
function genTypes(): string {
  const blocks: string[] = []
  for (const [name, schema] of Object.entries(schemas)) {
    const t = tsType(schema)
    if (t.startsWith("{") || t.startsWith("(")) {
      blocks.push(`export type ${name} = ${t};`)
    } else if (t.includes(" | ")) {
      blocks.push(`export type ${name} = ${t};`)
    } else if (t.includes(" & ")) {
      blocks.push(`export type ${name} = ${t};`)
    } else {
      blocks.push(`export interface ${name} {` )
      // object-like: 复用 tsType 逻辑的字段
      const props = schema.properties ?? {}
      for (const [k, v] of Object.entries(props)) {
        const required = schema.required?.includes(k)
        const opt = required ? "" : "?"
        blocks.push(`  ${k}${opt}: ${tsType(v)};`)
      }
      blocks.push("}")
    }
  }
  return [
    "/* 生成物（只读勿手改）—— 由 scripts/generate.ts 从 openapi.json 契约快照生成 */",
    "",
    ...blocks,
    "",
  ].join("\n")
}

// ---------- 2) client.ts ----------
function dataTypeOf(response: any): string {
  const content = response?.content?.["application/json"]
  let s = content?.schema
  if (!s) return "unknown"
  if (s.$ref) s = schemas[refName(s.$ref)]
  // ApiResponse_Xxx_ 的 data 是 anyOf [$ref, null] 或 object
  const data = s?.properties?.data
  if (!data) return "unknown"
  const nonNull = (data.anyOf ?? [data]).filter((x: any) => x.type !== "null")
  if (nonNull.length === 0) return "unknown"
  const first = nonNull[0]
  if (first.$ref) {
    const name = refName(first.$ref)
    // 解包：去掉 ApiResponse_ 包装，data 类型就是具体 Xxx
    const inner = name.match(/^ApiResponse_(.+)_$/)
    if (inner) return inner[1]
    return name
  }
  return tsType(first)
}

function fnName(path: string): string {
  const trimmed = path.replace(/^\/api\/v1\//, "")
  const parts = trimmed.split("/").filter(Boolean)
  if (parts.length === 0) return "index"
  return parts
    .map((s, i) => {
      const clean = camel(s.replace(/[{}]/g, ""))
      return i === 0 ? clean : clean.charAt(0).toUpperCase() + clean.slice(1)
    })
    .join("")
}

function pathParams(path: string): string[] {
  return [...path.matchAll(/\{([^}]+)\}/g)].map((m) => m[1])
}

function queryParams(operation: any): { name: string; required: boolean; type: string }[] {
  return (operation.parameters ?? [])
    .filter((p: any) => p.in === "query")
    .map((p: any) => ({
      name: p.name,
      required: !!p.required,
      type: tsType(p.schema),
    }))
}

function bodySchema(operation: any): any {
  return operation.requestBody?.content?.["application/json"]?.schema
}

function genClient(): string {
  const lines: string[] = []
  const typeImports = new Set<string>()
  // 同名路径多方法时函数名加方法后缀，避免重复定义（如 GET+POST /admin/knowledge）
  const methodCount: Record<string, number> = {}
  for (const [path, item] of Object.entries(paths)) {
    methodCount[path] = httpMethods.filter((m) => item[m]).length
  }
  for (const [path, item] of Object.entries(paths)) {
    for (const method of httpMethods) {
      const op = item[method]
      if (!op) continue
      const base = fnName(path)
      const name = methodCount[path] > 1 ? base + method.charAt(0).toUpperCase() + method.slice(1) : base
      const params = pathParams(path)
      const queries = queryParams(op)
      const body = bodySchema(op)
      const resp = op.responses?.["200"] ?? op.responses?.["201"]
      const respType = dataTypeOf(resp)

      // 跳过二进制/未类型化接口：FastAPI 对 Response 默认按 application/json 输出空 schema（{}），
      // 如 /documents/{id}/file 源文件直读 → 由 http.ts 手写 requestBlob 封装
      const jsonSchema = resp?.content?.["application/json"]?.schema
      const isTypedJson = !!jsonSchema && Object.keys(jsonSchema).length > 0
      if (!isTypedJson) continue

      const argParts: string[] = []
      for (const p of params) argParts.push(`${camel(p)}: string`)
      for (const q of queries) argParts.push(`${camel(q.name)}${q.required ? "" : "?"}: ${q.type}`)
      if (body) {
        const bt = body.$ref ? refName(body.$ref) : tsType(body)
        argParts.push(`body: ${bt}`)
        if (/^[A-Z]\w*$/.test(bt)) typeImports.add(bt)
      }

      // URL 模板：{vendor_id} -> ${vendorId}
      const urlTpl = path.replace(/\{([^}]+)\}/g, (_m, n: string) => "${" + camel(n) + "}")
      const urlArg = urlTpl.includes("${") ? "`" + urlTpl + "`" : JSON.stringify(urlTpl)

      const optsParts: string[] = [`method: "${method.toUpperCase()}"`]
      if (body) optsParts.push("body")
      if (queries.length) {
        const qNames = queries.map((q) => camel(q.name))
        optsParts.push(`query: { ${qNames.join(", ")} }`)
      }

      if (/^[A-Z]\w*$/.test(respType)) typeImports.add(respType)

      lines.push(`export async function ${name}(${argParts.join(", ")}): Promise<${respType}> {`)
      lines.push(`  return request<${respType}>(${urlArg}, { ${optsParts.join(", ")} })`)
      lines.push(`}`)
      lines.push("")
    }
  }
  const header = [
    "/* 生成物（只读勿手改）—— 由 scripts/generate.ts 从 openapi.json 契约快照生成 */",
    "/* API 客户端：统一经 http.request 封装（JWT 注入 + 统一响应 {code,message,data} 解包） */",
    "import { request } from \"./http\"",
    typeImports.size ? `import type { ${[...typeImports].join(", ")} } from "./types"` : "",
    "",
  ]
  return [...header, ...lines].join("\n")
}

// ---------- 3) msw/handlers.ts ----------
// 路径加 "*" 通配前缀：匹配任意 host（Node smoke 与浏览器同源均适用）
function mswPath(path: string): string {
  return "*" + path.replace(/\{([^}]+)\}/g, ":$1")
}

function genHandlers(): string {
  const lines: string[] = []
  for (const [path, item] of Object.entries(paths)) {
    for (const method of httpMethods) {
      const op = item[method]
      if (!op) continue
      const key = `${method.toUpperCase()} ${path}`
      lines.push(`  http.${method}(${JSON.stringify(mswPath(path))}, async ({ request }) => {`)
      lines.push(`    const data = await resolveMock(${JSON.stringify(key)}, request)`)
      lines.push(`    return HttpResponse.json({ code: 0, message: "ok", data })`)
      lines.push(`  }),`)
    }
  }
  return [
    "/* 生成物（只读勿手改）—— 由 scripts/generate.ts 从 openapi.json 契约快照生成 */",
    "/* MSW handlers：契约派生，数据来自 src/msw/mockData.ts（T1.9 丰富） */",
    "import { http, HttpResponse } from \"msw\"",
    "import { resolveMock } from \"./mockData\"",
    "",
    "export const handlers = [",
    ...lines,
    "  http.get(\"*/healthz\", () => HttpResponse.json({ code: 0, message: \"ok\", data: { status: \"ok\" } }))",
    "]",
    "",
  ].join("\n")
}

// ---------- write ----------
mkdirSync(outDir, { recursive: true })
mkdirSync(join(outDir, "msw"), { recursive: true })
writeFileSync(join(outDir, "types.ts"), genTypes(), "utf-8")
writeFileSync(join(outDir, "client.ts"), genClient(), "utf-8")
writeFileSync(join(outDir, "msw", "handlers.ts"), genHandlers(), "utf-8")
console.log("generated: src/types.ts, src/client.ts, src/msw/handlers.ts")
