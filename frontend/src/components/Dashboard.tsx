import { useState, useEffect } from 'react'
import { Wind, Zap, TrendingDown, Activity, Sparkles } from 'lucide-react'
import { useSimulationStore } from '../store/simulationStore'
import { layoutApi, windApi, simulationApi } from '../services/api'
import TurbineMap from './TurbineMap'
import WindDirectionSlider from './WindDirectionSlider'
import PowerLossChart from './PowerLossChart'

export default function Dashboard() {
  const {
    layout,
    setLayout,
    setWindData,
    windDirection,
    setWindDirection,
    windSpeed,
    setWindSpeed,
    wakeModel,
    quickResult,
    setQuickResult,
    wakeDecayCoefficient,
    isLoading,
    setIsLoading,
    setError,
  } = useSimulationStore()

  const [initialized, setInitialized] = useState(false)

  // Load sample data on mount
  useEffect(() => {
    const loadSampleData = async () => {
      if (initialized) return
      setIsLoading(true)
      try {
        const [sampleLayout, sampleWindData] = await Promise.all([
          layoutApi.getSample(),
          windApi.getSample(),
        ])
        setLayout(sampleLayout)
        setWindData(sampleWindData)
        setInitialized(true)
      } catch (err) {
        setError('Failed to load sample data')
        console.error(err)
      } finally {
        setIsLoading(false)
      }
    }
    loadSampleData()
  }, [initialized])

  // Run simulation when direction/speed changes
  useEffect(() => {
    const runSimulation = async () => {
      if (!layout) return
      setIsLoading(true)
      try {
        const result = await simulationApi.runQuick(
          layout,
          windDirection,
          windSpeed,
          wakeModel,
          wakeDecayCoefficient
        )
        setQuickResult(result)
      } catch (err) {
        setError('Simulation failed')
        console.error(err)
      } finally {
        setIsLoading(false)
      }
    }

    const debounce = setTimeout(runSimulation, 300)
    return () => clearTimeout(debounce)
  }, [layout, windDirection, windSpeed, wakeModel, wakeDecayCoefficient])

  const stats = [
    {
      label: 'Total Power',
      value: quickResult ? `${(quickResult.total_power_kw / 1000).toFixed(1)} MW` : '-',
      icon: Zap,
      color: 'text-emerald-600',
      bgClass: 'stat-green',
      glowClass: 'glow-green',
      iconBg: 'bg-emerald-500',
    },
    {
      label: 'Wake Loss',
      value: quickResult ? `${quickResult.wake_loss_percent.toFixed(1)}%` : '-',
      icon: TrendingDown,
      color: 'text-orange-600',
      bgClass: 'stat-orange',
      glowClass: 'glow-orange',
      iconBg: 'bg-orange-500',
    },
    {
      label: 'Turbines in Wake',
      value: quickResult ? `${quickResult.turbines_in_wake}` : '-',
      icon: Wind,
      color: 'text-gray-600',
      bgClass: 'stat-gray',
      glowClass: 'glow-gray',
      iconBg: 'bg-gray-500',
    },
    {
      label: 'Capacity Factor',
      value: quickResult ? `${quickResult.capacity_factor_percent.toFixed(1)}%` : '-',
      icon: Activity,
      color: 'text-orange-700',
      bgClass: 'stat-orange',
      glowClass: 'glow-orange',
      iconBg: 'bg-orange-600',
    },
  ]

  return (
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-orange-600 via-orange-500 to-amber-500 p-6 text-white shadow-xl">
        <div className="absolute top-0 right-0 -mt-4 -mr-4 h-32 w-32 rounded-full bg-white/10 blur-2xl"></div>
        <div className="absolute bottom-0 left-0 -mb-4 -ml-4 h-24 w-24 rounded-full bg-white/10 blur-xl"></div>
        <div className="relative z-10 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2">
              Real-Time Simulation Dashboard
              <Sparkles className="w-6 h-6 text-yellow-300" />
            </h2>
            <p className="text-orange-100 mt-1">
              Adjust wind parameters to see instant wake loss calculations
            </p>
          </div>
          <div className="hidden md:flex items-center gap-2 bg-white/10 px-4 py-2 rounded-xl backdrop-blur-sm">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            <span className="text-sm font-medium">Live Simulation</span>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {stats.map((stat, index) => {
          const Icon = stat.icon
          return (
            <div
              key={stat.label}
              className={`card-hover ${stat.bgClass} rounded-2xl p-5 border border-white/50 shadow-lg relative overflow-hidden`}
              style={{ animationDelay: `${index * 100}ms` }}
            >
              <div className="absolute top-0 right-0 w-20 h-20 bg-white/20 rounded-full -mr-10 -mt-10 blur-xl"></div>
              <div className="relative z-10 flex items-center gap-4">
                <div className={`p-3 rounded-xl ${stat.iconBg} shadow-lg`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-500">{stat.label}</p>
                  <p className={`text-2xl font-bold ${stat.color}`}>
                    {isLoading ? (
                      <span className="inline-block w-16 h-7 shimmer rounded"></span>
                    ) : (
                      stat.value
                    )}
                  </p>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map */}
        <div className="lg:col-span-2 bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200/50 overflow-hidden">
          <div className="p-5 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-bold text-gray-800 text-lg">Wind Farm Layout</h2>
                <p className="text-sm text-gray-500">
                  {layout ? (
                    <span className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                      {layout.turbines.length} turbines loaded
                    </span>
                  ) : (
                    'Loading...'
                  )}
                </p>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-100 px-3 py-1.5 rounded-lg">
                <Wind className="w-4 h-4" />
                {windDirection}° @ {windSpeed} m/s
              </div>
            </div>
          </div>
          <div className="h-[500px]">
            <TurbineMap
              layout={layout}
              windDirection={windDirection}
              turbineResults={quickResult?.turbine_results}
            />
          </div>
        </div>

        {/* Controls */}
        <div className="space-y-5">
          {/* Wind Direction */}
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200/50 p-5 card-hover">
            <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
              <div className="p-2 bg-orange-100 rounded-lg">
                <Wind className="w-4 h-4 text-orange-600" />
              </div>
              Wind Direction
            </h3>
            <WindDirectionSlider
              value={windDirection}
              onChange={setWindDirection}
            />
          </div>

          {/* Wind Speed */}
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200/50 p-5 card-hover">
            <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
              <div className="p-2 bg-gray-100 rounded-lg">
                <Activity className="w-4 h-4 text-gray-600" />
              </div>
              Wind Speed
            </h3>
            <div className="space-y-3">
              <div className="relative">
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
              <div className="flex justify-between items-center text-sm">
                <span className="text-gray-400">3 m/s</span>
                <span className="font-bold text-orange-600 bg-orange-50 px-3 py-1 rounded-full">
                  {windSpeed} m/s
                </span>
                <span className="text-gray-400">25 m/s</span>
              </div>
            </div>
          </div>

          {/* Power Loss Chart */}
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200/50 p-5 card-hover">
            <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
              <div className="p-2 bg-emerald-100 rounded-lg">
                <Zap className="w-4 h-4 text-emerald-600" />
              </div>
              Power by Turbine
            </h3>
            <PowerLossChart results={quickResult?.turbine_results} />
          </div>
        </div>
      </div>
    </div>
  )
}
