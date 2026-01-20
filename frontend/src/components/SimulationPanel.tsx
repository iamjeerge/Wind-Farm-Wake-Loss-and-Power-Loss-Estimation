import { useState } from 'react'
import { Play, Settings, Wind, Zap, RotateCcw, ChevronDown } from 'lucide-react'
import { useSimulationStore, WakeModelType } from '../store/simulationStore'
import { simulationApi } from '../services/api'
import TurbineMap from './TurbineMap'
import WindDirectionSlider from './WindDirectionSlider'

const WAKE_MODELS: { value: WakeModelType; label: string; description: string }[] = [
  {
    value: 'jensen',
    label: 'Jensen (Park)',
    description: 'Classic linear wake expansion model, fast computation',
  },
  {
    value: 'bastankhah',
    label: 'Bastankhah-Porté-Agel',
    description: 'Gaussian wake model with turbulence intensity effects',
  },
]

const SUPERPOSITION_METHODS = [
  { value: 'quadratic', label: 'Quadratic (RSS)', description: 'Root sum of squares' },
  { value: 'linear', label: 'Linear Sum', description: 'Simple linear addition' },
  { value: 'max', label: 'Maximum', description: 'Take maximum deficit only' },
]

export default function SimulationPanel() {
  const {
    layout,
    windData,
    windDirection,
    setWindDirection,
    windSpeed,
    setWindSpeed,
    wakeModel,
    setWakeModel,
    wakeDecayCoefficient,
    setWakeDecayCoefficient,
    turbulenceIntensity,
    setTurbulenceIntensity,
    superpositionMethod,
    setSuperpositionMethod,
    quickResult,
    setQuickResult,
    fullResult,
    setFullResult,
    isLoading,
    setIsLoading,
    setError,
  } = useSimulationStore()

  const [showAdvanced, setShowAdvanced] = useState(false)
  const [simulationType, setSimulationType] = useState<'quick' | 'full'>('quick')

  const handleRunSimulation = async () => {
    if (!layout) {
      setError('Please load a turbine layout first')
      return
    }

    setIsLoading(true)
    try {
      if (simulationType === 'quick') {
        const result = await simulationApi.runQuick(
          layout,
          windDirection,
          windSpeed,
          wakeModel,
          wakeDecayCoefficient
        )
        setQuickResult(result)
      } else {
        const result = await simulationApi.runFull({
          layout,
          wind_data: windData,
          wake_model: wakeModel,
          wake_decay_coefficient: wakeDecayCoefficient,
          turbulence_intensity: turbulenceIntensity,
          superposition_method: superpositionMethod,
        })
        setFullResult(result)
      }
    } catch (err) {
      setError('Simulation failed')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleReset = () => {
    setWindDirection(270)
    setWindSpeed(10)
    setWakeModel('jensen')
    setWakeDecayCoefficient(0.04)
    setTurbulenceIntensity(0.06)
    setSuperpositionMethod('quadratic')
    setQuickResult(null)
    setFullResult(null)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Simulation</h2>
          <p className="text-slate-500">Configure and run wake loss simulations</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleReset}
            className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors flex items-center gap-2"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>
          <button
            onClick={handleRunSimulation}
            disabled={isLoading || !layout}
            className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run Simulation
              </>
            )}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Configuration Panel */}
        <div className="space-y-4">
          {/* Simulation Type */}
          <div className="bg-white rounded-xl shadow-sm border p-5">
            <h3 className="font-semibold text-slate-800 mb-4">Simulation Type</h3>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setSimulationType('quick')}
                className={`p-3 rounded-lg border-2 transition-colors ${
                  simulationType === 'quick'
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <Zap className={`w-5 h-5 mx-auto mb-1 ${
                  simulationType === 'quick' ? 'text-primary-600' : 'text-slate-400'
                }`} />
                <div className="font-medium text-sm">Quick</div>
                <div className="text-xs text-slate-500">Single direction</div>
              </button>
              <button
                onClick={() => setSimulationType('full')}
                className={`p-3 rounded-lg border-2 transition-colors ${
                  simulationType === 'full'
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <Wind className={`w-5 h-5 mx-auto mb-1 ${
                  simulationType === 'full' ? 'text-primary-600' : 'text-slate-400'
                }`} />
                <div className="font-medium text-sm">Full AEP</div>
                <div className="text-xs text-slate-500">All directions</div>
              </button>
            </div>
          </div>

          {/* Wake Model */}
          <div className="bg-white rounded-xl shadow-sm border p-5">
            <h3 className="font-semibold text-slate-800 mb-4">Wake Model</h3>
            <div className="space-y-2">
              {WAKE_MODELS.map((model) => (
                <button
                  key={model.value}
                  onClick={() => setWakeModel(model.value)}
                  className={`w-full text-left p-3 rounded-lg border-2 transition-colors ${
                    wakeModel === model.value
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="font-medium text-sm">{model.label}</div>
                  <div className="text-xs text-slate-500">{model.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Wind Conditions (for quick sim) */}
          {simulationType === 'quick' && (
            <div className="bg-white rounded-xl shadow-sm border p-5">
              <h3 className="font-semibold text-slate-800 mb-4">Wind Conditions</h3>
              <div className="space-y-6">
                <WindDirectionSlider value={windDirection} onChange={setWindDirection} />
                <div>
                  <label className="block text-sm font-medium text-slate-600 mb-2">
                    Wind Speed: {windSpeed} m/s
                  </label>
                  <input
                    type="range"
                    min={3}
                    max={25}
                    step={0.5}
                    value={windSpeed}
                    onChange={(e) => setWindSpeed(parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Advanced Settings */}
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="w-full p-4 flex items-center justify-between hover:bg-slate-50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Settings className="w-5 h-5 text-slate-400" />
                <span className="font-semibold text-slate-800">Advanced Settings</span>
              </div>
              <ChevronDown
                className={`w-5 h-5 text-slate-400 transition-transform ${
                  showAdvanced ? 'rotate-180' : ''
                }`}
              />
            </button>
            
            {showAdvanced && (
              <div className="p-5 pt-0 space-y-4">
                {/* Wake Decay */}
                <div>
                  <label className="block text-sm font-medium text-slate-600 mb-2">
                    Wake Decay Coefficient (k): {wakeDecayCoefficient.toFixed(3)}
                  </label>
                  <input
                    type="range"
                    min={0.01}
                    max={0.1}
                    step={0.005}
                    value={wakeDecayCoefficient}
                    onChange={(e) => setWakeDecayCoefficient(parseFloat(e.target.value))}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-slate-400 mt-1">
                    <span>0.01 (stable)</span>
                    <span>0.1 (turbulent)</span>
                  </div>
                </div>

                {/* Turbulence Intensity */}
                <div>
                  <label className="block text-sm font-medium text-slate-600 mb-2">
                    Turbulence Intensity: {(turbulenceIntensity * 100).toFixed(1)}%
                  </label>
                  <input
                    type="range"
                    min={0.02}
                    max={0.2}
                    step={0.01}
                    value={turbulenceIntensity}
                    onChange={(e) => setTurbulenceIntensity(parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>

                {/* Superposition Method */}
                <div>
                  <label className="block text-sm font-medium text-slate-600 mb-2">
                    Wake Superposition
                  </label>
                  <select
                    value={superpositionMethod}
                    onChange={(e) => setSuperpositionMethod(e.target.value as any)}
                    className="w-full p-2 border rounded-lg bg-white text-sm"
                  >
                    {SUPERPOSITION_METHODS.map((method) => (
                      <option key={method.value} value={method.value}>
                        {method.label} - {method.description}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Map & Results */}
        <div className="lg:col-span-2 space-y-4">
          {/* Map */}
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            <div className="p-4 border-b">
              <h3 className="font-semibold text-slate-800">Simulation Preview</h3>
            </div>
            <div className="h-[400px]">
              <TurbineMap
                layout={layout}
                windDirection={windDirection}
                turbineResults={quickResult?.turbine_results}
              />
            </div>
          </div>

          {/* Quick Results */}
          {quickResult && (
            <div className="bg-white rounded-xl shadow-sm border p-5">
              <h3 className="font-semibold text-slate-800 mb-4">Quick Simulation Results</h3>
              <div className="grid grid-cols-4 gap-4">
                <div className="bg-green-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-green-600">
                    {(quickResult.total_power_kw / 1000).toFixed(1)} MW
                  </div>
                  <div className="text-sm text-green-700">Total Power</div>
                </div>
                <div className="bg-orange-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-orange-600">
                    {quickResult.wake_loss_percent.toFixed(1)}%
                  </div>
                  <div className="text-sm text-orange-700">Wake Loss</div>
                </div>
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-blue-600">
                    {quickResult.turbines_in_wake}
                  </div>
                  <div className="text-sm text-blue-700">Turbines in Wake</div>
                </div>
                <div className="bg-purple-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-purple-600">
                    {quickResult.capacity_factor_percent.toFixed(1)}%
                  </div>
                  <div className="text-sm text-purple-700">Capacity Factor</div>
                </div>
              </div>
            </div>
          )}

          {/* Full Results */}
          {fullResult && (
            <div className="bg-white rounded-xl shadow-sm border p-5">
              <h3 className="font-semibold text-slate-800 mb-4">Full AEP Results</h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-green-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-green-600">
                    {fullResult.aep_gwh.toFixed(1)} GWh
                  </div>
                  <div className="text-sm text-green-700">Annual Energy Production</div>
                </div>
                <div className="bg-orange-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-orange-600">
                    {fullResult.wake_loss_percent.toFixed(1)}%
                  </div>
                  <div className="text-sm text-orange-700">Average Wake Loss</div>
                </div>
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-blue-600">
                    {fullResult.capacity_factor_percent.toFixed(1)}%
                  </div>
                  <div className="text-sm text-blue-700">Capacity Factor</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
