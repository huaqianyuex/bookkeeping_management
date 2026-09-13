import request from './request'

/** 会话列表：keyword 可选；sort: updated|created；order: asc|desc */
export function listSessions({ keyword, sort, order, page, size } = {}) {
  return request.get('/ai/sessions', { params: { keyword, sort, order, page, size } })
}

export function createSession(title) {
  return request.post('/ai/sessions', { title })
}

export function renameSession(id, title) {
  return request.patch(`/ai/sessions/${id}`, { title })
}

export function deleteSession(id) {
  return request.delete(`/ai/sessions/${id}`)
}

export function batchDeleteSessions(ids) {
  return request.post('/ai/sessions/batch-delete', { ids })
}

export function getSessionMessages(id) {
  return request.get(`/ai/sessions/${id}/messages`)
}
