import { useState, useEffect } from 'react'
import { Wind, Gauge, BarChart3, Download, Settings, Sparkles } from 'lucide-react'
import Dashboard from './components/Dashboard'
import LayoutPanel from './components/LayoutPanel'
import SimulationPanel from './components/SimulationPanel'
import ResultsPanel from './components/ResultsPanel'
import { useSimulationStore } from './store/simulationStore'
import { layoutApi, windApi } from './services/api'

type Tab = 'dashboard' | 'layout' | 'simulation' | 'results'

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard')
  const { hasResults, layout, setLayout, setWindData } = useSimulationStore()

  // Load sample data on app start
  useEffect(() => {
    const loadInitialData = async () => {
      if (!layout) {
        try {
          const [sampleLayout, sampleWind] = await Promise.all([
            layoutApi.getSample(),
            windApi.getSample(),
          ])
          setLayout(sampleLayout)
          setWindData(sampleWind)
        } catch (error) {
          console.error('Failed to load initial data:', error)
        }
      }
    }
    loadInitialData()
  }, [])

  const tabs = [
    { id: 'dashboard' as Tab, label: 'Dashboard', icon: Gauge },
    { id: 'layout' as Tab, label: 'Layout', icon: Wind },
    { id: 'simulation' as Tab, label: 'Simulation', icon: Settings },
    { id: 'results' as Tab, label: 'Results', icon: BarChart3, disabled: !hasResults },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-orange-50/30 to-gray-100">
      {/* Header */}
      <header className="animated-gradient text-white shadow-2xl relative overflow-hidden">
        <div className="absolute inset-0 opacity-20">
          <div className="absolute inset-0" style={{
            backgroundImage: 'radial-gradient(circle at 25% 25%, rgba(255,255,255,0.2) 2%, transparent 10%), radial-gradient(circle at 75% 75%, rgba(255,255,255,0.2) 2%, transparent 10%)',
            backgroundSize: '60px 60px'
          }}></div>
        </div>
        <div className="max-w-7xl mx-auto px-4 py-6 relative z-10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="absolute inset-0 bg-white/20 rounded-xl blur-lg"></div>
                <div className="relative bg-white/10 p-3 rounded-xl backdrop-blur-sm border border-white/20">
                  <Wind className="w-10 h-10 turbine-spin" />
                </div>
              </div>
              <div>
                <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
                  Wind Wake Loss Estimation
                  <Sparkles className="w-6 h-6 text-yellow-300 float" />
                </h1>
                <p className="text-orange-100 text-sm font-medium mt-1">
                  Physics-aware wind farm simulation platform
                </p>
              </div>
            </div>
            <button className="flex items-center gap-2 bg-white/10 hover:bg-white/20 px-5 py-2.5 rounded-xl transition-all duration-300 backdrop-blur-sm border border-white/20 hover:scale-105 hover:shadow-lg">
              <Download className="w-5 h-5" />
              <span className="font-medium">Export</span>
            </button>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white/80 backdrop-blur-md border-b border-gray-200/50 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex gap-2 py-1">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => !tab.disabled && setActiveTab(tab.id)}
                  disabled={tab.disabled}
                  className={`flex items-center gap-2 px-6 py-3 font-medium transition-all duration-300 rounded-lg my-1 ${
                    activeTab === tab.id
                      ? 'bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-lg shadow-orange-500/30'
                      : tab.disabled
                      ? 'text-gray-300 cursor-not-allowed'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-orange-600'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${activeTab === tab.id ? '' : ''}`} />
                  {tab.label}
                </button>
              )
            })}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="animate-fadeIn">
          {activeTab === 'dashboard' && <Dashboard />}
          {activeTab === 'layout' && <LayoutPanel />}
          {activeTab === 'simulation' && <SimulationPanel />}
          {activeTab === 'results' && <ResultsPanel />}
        </div>
      </main>

      {/* Footer */}
      <footer className="glass-dark text-gray-300 py-8 mt-12">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Wind className="w-6 h-6 text-orange-400" />
              <span className="font-semibold text-white">Wind Wake Loss Tool</span>
            </div>
            <p className="text-sm text-gray-400 text-center">
              Jensen & Bastankhah wake models • Annual Energy Production • Interactive visualization
            </p>
            <div className="flex items-center gap-4 text-sm">
              <span className="px-3 py-1 bg-orange-500/20 text-orange-400 rounded-full border border-orange-500/30">
                v1.0.0
              </span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
