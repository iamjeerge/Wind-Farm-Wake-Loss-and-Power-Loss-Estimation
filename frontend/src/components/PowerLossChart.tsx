import { useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts'

interface TurbineResult {
  turbine_id: string
  power_kw: number
  wake_deficit: number
  effective_wind_speed: number
}

interface PowerLossChartProps {
  results?: TurbineResult[]
}

export default function PowerLossChart({ results }: PowerLossChartProps) {
  const chartData = useMemo(() => {
    if (!results) return []
    
    return results
      .map((r) => ({
        id: r.turbine_id.replace('T', ''),
        power: r.power_kw / 1000, // Convert to MW
        wakeLoss: r.wake_deficit * 100,
        effectiveWind: r.effective_wind_speed,
      }))
      .sort((a, b) => parseInt(a.id) - parseInt(b.id))
  }, [results])

  const averagePower = useMemo(() => {
    if (chartData.length === 0) return 0
    return chartData.reduce((sum, d) => sum + d.power, 0) / chartData.length
  }, [chartData])

  // Max power could be used for normalization if needed
  // const maxPower = useMemo(() => {
  //   if (chartData.length === 0) return 1
  //   return Math.max(...chartData.map((d) => d.power))
  // }, [chartData])

  if (!results || results.length === 0) {
    return (
      <div className="h-48 flex items-center justify-center text-slate-400">
        No simulation results
      </div>
    )
  }

  return (
    <div className="h-48">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="id"
            tick={{ fontSize: 10, fill: '#64748b' }}
            tickLine={false}
            axisLine={{ stroke: '#e2e8f0' }}
          />
          <YAxis
            tick={{ fontSize: 10, fill: '#64748b' }}
            tickLine={false}
            axisLine={{ stroke: '#e2e8f0' }}
            tickFormatter={(v) => `${v.toFixed(1)}`}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload || payload.length === 0) return null
              const data = payload[0].payload
              return (
                <div className="bg-white p-3 rounded-lg shadow-lg border text-sm">
                  <div className="font-bold text-slate-800 mb-1">Turbine T{data.id}</div>
                  <div className="text-green-600">Power: {data.power.toFixed(2)} MW</div>
                  <div className="text-orange-600">Wake Loss: {data.wakeLoss.toFixed(1)}%</div>
                  <div className="text-blue-600">
                    Wind: {data.effectiveWind.toFixed(1)} m/s
                  </div>
                </div>
              )
            }}
          />
          <ReferenceLine
            y={averagePower}
            stroke="#6366f1"
            strokeDasharray="5 5"
            label={{
              value: `Avg: ${averagePower.toFixed(2)} MW`,
              position: 'right',
              fill: '#6366f1',
              fontSize: 10,
            }}
          />
          <Bar dataKey="power" radius={[4, 4, 0, 0]}>
            {chartData.map((entry, index) => {
              // Color based on wake loss
              const lossRatio = entry.wakeLoss / 100
              const hue = (1 - lossRatio) * 120 // Green to red
              return (
                <Cell
                  key={`cell-${index}`}
                  fill={`hsl(${hue}, 70%, 50%)`}
                />
              )
            })}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
