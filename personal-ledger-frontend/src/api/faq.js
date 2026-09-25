import request from './request'

/** FAQ 知识库管理（管理端 /admin/faq）+ AI 索引重建（/ai/faq/rebuild） */

export function listFaq() {
  return request.get('/admin/faq')
}

export function createFaq(data) {
  // data: { question, answer, category }
  return request.post('/admin/faq', data)
}

export function updateFaq(id, data) {
  // data: { question?, answer?, category? }
  return request.put(`/admin/faq/${id}`, data)
}

export function deleteFaq(id) {
  return request.delete(`/admin/faq/${id}`)
}

/** 重建 FAQ 向量索引：成功 {success:true,count:n}；失败 {error} */
export function rebuildFaqIndex() {
  return request.post('/ai/faq/rebuild')
}
