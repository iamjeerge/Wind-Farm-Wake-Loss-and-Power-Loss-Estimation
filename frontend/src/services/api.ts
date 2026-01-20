import axios from 'axios'
import type {
  TurbineLayout,
  WindData,
  QuickResult,
  FullResult,
  WakeModelType,
  SuperpositionMethod,
} from '../store/simulationStore'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

export const layoutApi = {
  getSample: async (): Promise<TurbineLayout> => {
    const response = await api.get('/layout/sample')
    return response.data
  },

  upload: async (file: File): Promise<TurbineLayout> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post('/layout/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  validate: async (layout: TurbineLayout) => {
    const response = await api.post('/layout/validate', layout)
    return response.data
  },
}

export const windApi = {
  getSample: async (): Promise<WindData> => {
    const response = await api.get('/wind/sample')
    return response.data
  },

  getUniformRose: async (sectors: number = 36) => {
    const response = await api.get(`/wind/rose/uniform?sectors=${sectors}`)
    return response.data
  },

  uploadRose: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post('/wind/rose/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },
}

interface FullSimulationParams {
  layout: TurbineLayout
  wind_data: WindData | null
  wake_model: WakeModelType
  wake_decay_coefficient: number
  turbulence_intensity: number
  superposition_method: SuperpositionMethod
}

export const simulationApi = {
  runQuick: async (
    layout: TurbineLayout,
    windDirection: number,
    windSpeed: number,
    wakeModel: WakeModelType = 'jensen',
    wakeDecayCoefficient: number = 0.04
  ): Promise<QuickResult> => {
    const response = await api.post('/simulation/quick', {
      layout,
      wind_direction: windDirection,
      wind_speed: windSpeed,
      wake_model: wakeModel,
      wake_decay_coefficient: wakeDecayCoefficient,
    })
    return response.data
  },

  runFull: async (params: FullSimulationParams): Promise<FullResult> => {
    const response = await api.post('/simulation/full', params)
    return response.data
  },

  create: async (
    layout: TurbineLayout,
    windData: WindData,
    name: string = 'Simulation'
  ) => {
    const response = await api.post('/simulation/', {
      layout,
      wind_data: windData,
      name,
      compute_aep: true,
    })
    return response.data
  },

  getStatus: async (runId: string) => {
    const response = await api.get(`/simulation/${runId}/status`)
    return response.data
  },

  getResults: async (runId: string) => {
    const response = await api.get(`/simulation/${runId}/results`)
    return response.data
  },

  list: async () => {
    const response = await api.get('/simulation/')
    return response.data
  },
}

export const exportApi = {
  export: async (results: QuickResult | FullResult, format: 'csv' | 'json' | 'pdf'): Promise<Blob> => {
    const response = await api.post(
      `/export/${format}`,
      { results },
      { responseType: 'blob' }
    )
    return response.data
  },

  downloadCsv: (runId: string) => {
    window.open(`/api/v1/export/${runId}/csv`, '_blank')
  },

  downloadJson: (runId: string) => {
    window.open(`/api/v1/export/${runId}/json`, '_blank')
  },

  downloadPdf: (runId: string) => {
    window.open(`/api/v1/export/${runId}/pdf`, '_blank')
  },

  getSummary: async (runId: string) => {
    const response = await api.get(`/export/${runId}/summary`)
    return response.data
  },
}

export default api
