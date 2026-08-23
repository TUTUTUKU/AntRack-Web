/**
 * 从响应头解析文件名并触发浏览器下载
 */
export function downloadBlob(blob, contentDisposition) {
  let filename = 'export.xlsx'
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^"]+)"?/)
    if (match) {
      filename = decodeURIComponent(match[1])
    }
  }
  const url = window.URL.createObjectURL(new Blob([blob]))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}
