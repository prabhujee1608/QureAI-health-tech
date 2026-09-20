const api = async (path, options = {}) => {
  const isFormData = options.body instanceof FormData
  const response = await fetch(path, {
    headers: isFormData ? options.headers : { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!response.ok) throw new Error((await response.json()).detail || 'API request failed')
  return response.json()
}

export const getApiHealth = () => api('/api/health')
export const predictWait = (payload) => api('/api/predict', { method: 'POST', body: JSON.stringify(payload) })
export const explainPrediction = (payload) => api('/api/prediction-explanation', { method: 'POST', body: JSON.stringify(payload) })
export const getHospitalAvailability = (hospitalId) => api(`/api/availability/${hospitalId}`)

export const transcribeAudio = async (file) => {
  const form = new FormData()
  form.append('audio', file)
  return api('/api/transcribe', { method: 'POST', body: form, headers: {} })
}
