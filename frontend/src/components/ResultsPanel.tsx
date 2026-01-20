import { useState, useMemo } from 'react'
import {
  Download,
  FileText,
  FileSpreadsheet,
  FileJson,
  TrendingUp,
  TrendingDown,
  ArrowUpDown,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts'
import { useSimulationStore } from '../store/simulationStore'
import { exportApi } from '../services/api'

type SortField = 'id' | 'power' | 'wake_loss' | 'wind_speed'
type SortOrder = 'asc' | 'desc'

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

export default function ResultsPanel() {
  const { quickResult, fullResult, wakeModel, setError } = useSimulationStore()
  const [sortField, setSortField] = useState<SortField>('id')
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc')
  const [exporting, setExporting] = useState(false)

  const results = quickResult || fullResult
  const turbineResults = results?.turbine_results || []

  // Sort turbine results
  const sortedResults = useMemo(() => {
    return [...turbineResults].sort((a, b) => {
      let aVal: number, bVal: number
      switch (sortField) {
        case 'id':
          aVal = parseInt(a.turbine_id.replace(/\D/g, ''))
          bVal = parseInt(b.turbine_id.replace(/\D/g, ''))
          break
        case 'power':
          aVal = a.power_kw
          bVal = b.power_kw
          break
        case 'wake_loss':
          aVal = a.wake_deficit
          bVal = b.wake_deficit
          break
        case 'wind_speed':
          aVal = a.effective_wind_speed
          bVal = b.effective_wind_speed
          break
        default:
          return 0
      }
      return sortOrder === 'asc' ? aVal - bVal : bVal - aVal
    })
  }, [turbineResults, sortField, sortOrder])

  // Prepare chart data
  const powerChartData = useMemo(() => {
    return sortedResults.map((r) => ({
      id: r.turbine_id,
      power: r.power_kw / 1000,
      maxPower: 3.6, // Assuming 3.6 MW turbines
      loss: ((3.6 - r.power_kw / 1000) / 3.6) * 100,
    }))
  }, [sortedResults])

  const wakeLossDistribution = useMemo(() => {
    const bins = [
      { range: '0-5%', count: 0 },
      { range: '5-10%', count: 0 },
      { range: '10-15%', count: 0 },
      { range: '15-20%', count: 0 },
      { range: '20%+', count: 0 },
    ]
    
    turbineResults.forEach((r) => {
      const loss = r.wake_deficit * 100
      if (loss < 5) bins[0].count++
      else if (loss < 10) bins[1].count++
      else if (loss < 15) bins[2].count++
      else if (loss < 20) bins[3].count++
      else bins[4].count++
    })
    
    return bins
  }, [turbineResults])

  // Directional results for radar chart (from full simulation)
  const directionalData = useMemo(() => {
    if (!fullResult?.directional_results) return []
    return fullResult.directional_results.map((d: any) => ({
      direction: `${d.direction}°`,
      power: d.power_mw,
      loss: d.wake_loss_percent,
    }))
  }, [fullResult])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('asc')
    }
  }

  const handleExport = async (format: 'csv' | 'json' | 'pdf') => {
    if (!results) return
    
    setExporting(true)
    try {
      const blob = await exportApi.export(results, format)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `wake_analysis_results.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      setError(`Failed to export ${format.toUpperCase()}`)
      console.error(err)
    } finally {
      setExporting(false)
    }
  }

  if (!results) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-slate-400">
        <TrendingUp className="w-16 h-16 mb-4" />
        <h3 className="text-xl font-medium mb-2">No Results Yet</h3>
        <p>Run a simulation to see the results here</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Simulation Results</h2>
          <p className="text-slate-500">
            {wakeModel === 'jensen' ? 'Jensen Model' : 'Bastankhah Model'} • {turbineResults.length} turbines
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleExport('csv')}
            disabled={exporting}
            className="px-4 py-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            <FileSpreadsheet className="w-4 h-4" />
            CSV
          </button>
          <button
            onClick={() => handleExport('json')}
            disabled={exporting}
            className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            <FileJson className="w-4 h-4" />
            JSON
          </button>
          <button
            onClick={() => handleExport('pdf')}
            disabled={exporting}
            className="px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            <FileText className="w-4 h-4" />
            PDF
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-5 text-white">
          <div className="flex items-center gap-3 mb-2">
            <TrendingUp className="w-6 h-6 opacity-80" />
            <span className="font-medium opacity-80">Total Power</span>
          </div>
          <div className="text-3xl font-bold">
            {quickResult
              ? `${(quickResult.total_power_kw / 1000).toFixed(1)} MW`
              : `${fullResult?.aep_gwh.toFixed(1)} GWh/yr`}
          </div>
        </div>
        
        <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl p-5 text-white">
          <div className="flex items-center gap-3 mb-2">
            <TrendingDown className="w-6 h-6 opacity-80" />
            <span className="font-medium opacity-80">Wake Loss</span>
          </div>
          <div className="text-3xl font-bold">
            {results.wake_loss_percent?.toFixed(1) || '—'}%
          </div>
        </div>
        
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-5 text-white">
          <div className="flex items-center gap-3 mb-2">
            <Download className="w-6 h-6 opacity-80" />
            <span className="font-medium opacity-80">Capacity Factor</span>
          </div>
          <div className="text-3xl font-bold">
            {results.capacity_factor_percent?.toFixed(1) || '—'}%
          </div>
        </div>
        
        <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl p-5 text-white">
          <div className="flex items-center gap-3 mb-2">
            <TrendingUp className="w-6 h-6 opacity-80" />
            <span className="font-medium opacity-80">Turbines Affected</span>
          </div>
          <div className="text-3xl font-bold">
            {quickResult?.turbines_in_wake || '—'}
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Power by Turbine */}
        <div className="bg-white rounded-xl shadow-sm border p-5">
          <h3 className="font-semibold text-slate-800 mb-4">Power Output by Turbine</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={powerChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="id"
                  tick={{ fontSize: 10, fill: '#64748b' }}
                  interval={1}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: '#64748b' }}
                  label={{ value: 'MW', angle: -90, position: 'insideLeft', fontSize: 12 }}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.[0]) return null
                    const d = payload[0].payload
                    return (
                      <div className="bg-white p-3 rounded-lg shadow-lg border text-sm">
                        <div className="font-bold">{d.id}</div>
                        <div className="text-green-600">Power: {d.power.toFixed(2)} MW</div>
                        <div className="text-orange-600">Loss: {d.loss.toFixed(1)}%</div>
                      </div>
                    )
                  }}
                />
                <Bar dataKey="power" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Wake Loss Distribution */}
        <div className="bg-white rounded-xl shadow-sm border p-5">
          <h3 className="font-semibold text-slate-800 mb-4">Wake Loss Distribution</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={wakeLossDistribution.filter((d) => d.count > 0)}
                  dataKey="count"
                  nameKey="range"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ range, count }) => `${range}: ${count}`}
                >
                  {wakeLossDistribution.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Directional Analysis (for full simulation) */}
      {directionalData.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border p-5">
          <h3 className="font-semibold text-slate-800 mb-4">Directional Power Analysis</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={directionalData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="direction" tick={{ fontSize: 10 }} />
                <PolarRadiusAxis tick={{ fontSize: 10 }} />
                <Radar
                  name="Power (MW)"
                  dataKey="power"
                  stroke="#10b981"
                  fill="#10b981"
                  fillOpacity={0.3}
                />
                <Radar
                  name="Wake Loss (%)"
                  dataKey="loss"
                  stroke="#f59e0b"
                  fill="#f59e0b"
                  fillOpacity={0.3}
                />
                <Legend />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Turbine Results Table */}
      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <div className="p-5 border-b">
          <h3 className="font-semibold text-slate-800">Turbine Details</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50">
              <tr>
                <th className="text-left p-4">
                  <button
                    onClick={() => handleSort('id')}
                    className="flex items-center gap-1 font-medium text-slate-600 hover:text-slate-800"
                  >
                    Turbine ID
                    <ArrowUpDown className="w-4 h-4" />
                  </button>
                </th>
                <th className="text-left p-4">
                  <button
                    onClick={() => handleSort('power')}
                    className="flex items-center gap-1 font-medium text-slate-600 hover:text-slate-800"
                  >
                    Power Output
                    <ArrowUpDown className="w-4 h-4" />
                  </button>
                </th>
                <th className="text-left p-4">
                  <button
                    onClick={() => handleSort('wake_loss')}
                    className="flex items-center gap-1 font-medium text-slate-600 hover:text-slate-800"
                  >
                    Wake Loss
                    <ArrowUpDown className="w-4 h-4" />
                  </button>
                </th>
                <th className="text-left p-4">
                  <button
                    onClick={() => handleSort('wind_speed')}
                    className="flex items-center gap-1 font-medium text-slate-600 hover:text-slate-800"
                  >
                    Effective Wind
                    <ArrowUpDown className="w-4 h-4" />
                  </button>
                </th>
                <th className="text-left p-4 font-medium text-slate-600">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {sortedResults.map((result) => {
                const lossPercent = result.wake_deficit * 100
                const statusColor =
                  lossPercent < 5
                    ? 'bg-green-100 text-green-700'
                    : lossPercent < 15
                    ? 'bg-yellow-100 text-yellow-700'
                    : 'bg-red-100 text-red-700'

                return (
                  <tr key={result.turbine_id} className="hover:bg-slate-50">
                    <td className="p-4 font-medium">{result.turbine_id}</td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-slate-100 rounded-full h-2 max-w-24">
                          <div
                            className="bg-green-500 h-2 rounded-full"
                            style={{ width: `${(result.power_kw / 3600) * 100}%` }}
                          />
                        </div>
                        <span className="text-slate-600">
                          {(result.power_kw / 1000).toFixed(2)} MW
                        </span>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className="text-orange-600 font-medium">
                        {lossPercent.toFixed(1)}%
                      </span>
                    </td>
                    <td className="p-4 text-slate-600">
                      {result.effective_wind_speed.toFixed(1)} m/s
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColor}`}>
                        {lossPercent < 5 ? 'Optimal' : lossPercent < 15 ? 'Moderate' : 'High Loss'}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
