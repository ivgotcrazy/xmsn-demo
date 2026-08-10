/**
 * 文件上传封装（架构 5.4 例外：multipart 上传不做 mock 模拟，真实联调 M2；
 * M1 阶段经 mock 拦截返回演示结果）。生成的 client 未覆盖 multipart，故手写。
 */
import { request, type UploadResult } from "@xmsn/api"

/** 通用文件上传（营业执照 / 能力文档）。 */
export async function uploadFile(file: File): Promise<UploadResult> {
  const fd = new FormData()
  fd.append("file", file)
  return request<UploadResult>("/api/v1/files/upload", { method: "POST", formData: fd })
}

/** 能力录入：仅上传文档（AI 解析为能力档案）。 */
export async function uploadCapability(payload: {
  vendorId: string
  files: File[]
}): Promise<import("@xmsn/api").CapabilityOut> {
  const fd = new FormData()
  fd.append("vendor_id", payload.vendorId)
  payload.files.forEach((f) => fd.append("documents", f))
  return request<import("@xmsn/api").CapabilityOut>("/api/v1/vendor/capability/upload", {
    method: "POST",
    formData: fd,
  })
}
