import { create } from 'zustand'

export type WakeModelType = 'jensen' | 'bastankhah'
export type SuperpositionMethod = 'quadratic' | 'linear' | 'max'

export interface Turbine {
  id: string
  name?: string
  latitude: number
  longitude: number
  x?: number
  y?: number
  hub_height: number
  rotor_diameter: number
  rated_power?: number
  thrust_coefficient?: number
}

export interface TurbineLayout {
  turbines: Turbine[]
  name?: string
  center_lat: number
  center_lon: number
  reference_latitude?: number | null
  reference_longitude?: number | null
}

export interface WindRoseEntry {
  direction: number
  probability: number
  sector_width?: number
}

export interface WindRose {
  entries: WindRoseEntry[]
  name?: string
}

export interface WeibullParameters {
  shape: number
  scale: number
}

export interface WindData {
  wind_rose: WindRose
  weibull: WeibullParameters
}

export interface TurbineResult {
  turbine_id: string
  turbine_name?: string
  power_kw: number
  wake_deficit: number
  loss_percent?: number
  effective_wind_speed: number
  effective_speed_ms?: number
}

export interface QuickResult {
  wind_direction: number
  wind_speed: number
  total_power_kw: number
  total_loss_kw?: number
  wake_loss_percent: number
  capacity_factor_percent: number
  turbines_in_wake: number
  turbine_results: TurbineResult[]
}

export interface DirectionalResult {
  direction: number
  power_mw: number
  wake_loss_percent: number
}

export interface FullResult {
  aep_gwh: number
  gross_aep_gwh?: number
  wake_loss_percent: number
  capacity_factor_percent: number
  turbine_results: TurbineResult[]
  directional_results?: DirectionalResult[]
}

export interface AEPResult {
  gross_aep_mwh: number
  net_aep_mwh: number
  wake_loss_mwh: number
  wake_loss_percent: number
  net_capacity_factor: number
}

interface SimulationStore {
  // Layout
  layout: TurbineLayout | null
  setLayout: (layout: TurbineLayout | null) => void

  // Wind data
  windData: WindData | null
  setWindData: (windData: WindData | null) => void

  // Simulation config
  wakeModel: WakeModelType
  setWakeModel: (model: WakeModelType) => void
  wakeDecayCoefficient: number
  setWakeDecayCoefficient: (k: number) => void
  turbulenceIntensity: number
  setTurbulenceIntensity: (ti: number) => void
  superpositionMethod: SuperpositionMethod
  setSuperpositionMethod: (method: SuperpositionMethod) => void
  windDirection: number
  setWindDirection: (dir: number) => void
  windSpeed: number
  setWindSpeed: (speed: number) => void

  // Results
  quickResult: QuickResult | null
  setQuickResult: (result: QuickResult | null) => void
  fullResult: FullResult | null
  setFullResult: (result: FullResult | null) => void
  aepResult: AEPResult | null
  setAepResult: (result: AEPResult | null) => void
  hasResults: boolean

  // Loading state
  isLoading: boolean
  setIsLoading: (loading: boolean) => void
  error: string | null
  setError: (error: string | null) => void
}

export const useSimulationStore = create<SimulationStore>((set, get) => ({
  // Layout
  layout: null,
  setLayout: (layout) => set({ layout }),

  // Wind data
  windData: null,
  setWindData: (windData) => set({ windData }),

  // Simulation config
  wakeModel: 'jensen',
  setWakeModel: (wakeModel) => set({ wakeModel }),
  wakeDecayCoefficient: 0.04,
  setWakeDecayCoefficient: (wakeDecayCoefficient) => set({ wakeDecayCoefficient }),
  turbulenceIntensity: 0.06,
  setTurbulenceIntensity: (turbulenceIntensity) => set({ turbulenceIntensity }),
  superpositionMethod: 'quadratic',
  setSuperpositionMethod: (superpositionMethod) => set({ superpositionMethod }),
  windDirection: 270,
  setWindDirection: (windDirection) => set({ windDirection }),
  windSpeed: 10,
  setWindSpeed: (windSpeed) => set({ windSpeed }),

  // Results
  quickResult: null,
  setQuickResult: (quickResult) => set({ quickResult }),
  fullResult: null,
  setFullResult: (fullResult) => set({ fullResult }),
  aepResult: null,
  setAepResult: (aepResult) => set({ aepResult }),
  get hasResults() {
    const state = get()
    return state.quickResult !== null || state.fullResult !== null
  },

  // Loading state
  isLoading: false,
  setIsLoading: (isLoading) => set({ isLoading }),
  error: null,
  setError: (error) => set({ error }),
}))
