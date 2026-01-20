import { useCallback } from 'react'
import { Compass } from 'lucide-react'

interface WindDirectionSliderProps {
  value: number
  onChange: (value: number) => void
}

const CARDINAL_DIRECTIONS = [
  { angle: 0, label: 'N' },
  { angle: 45, label: 'NE' },
  { angle: 90, label: 'E' },
  { angle: 135, label: 'SE' },
  { angle: 180, label: 'S' },
  { angle: 225, label: 'SW' },
  { angle: 270, label: 'W' },
  { angle: 315, label: 'NW' },
]

export default function WindDirectionSlider({ value, onChange }: WindDirectionSliderProps) {
  const handleSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange(parseInt(e.target.value, 10))
    },
    [onChange]
  )

  const handleCardinalClick = useCallback(
    (angle: number) => {
      onChange(angle)
    },
    [onChange]
  )

  // Get cardinal direction name
  const getCardinalName = (angle: number): string => {
    const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    const index = Math.round(angle / 45) % 8
    return directions[index]
  }

  return (
    <div className="space-y-4">
      {/* Compass visualization */}
      <div className="relative w-40 h-40 mx-auto">
        {/* Compass circle */}
        <div className="absolute inset-0 rounded-full border-4 border-slate-200 bg-gradient-to-b from-slate-50 to-slate-100">
          {/* Cardinal direction buttons */}
          {CARDINAL_DIRECTIONS.map(({ angle, label }) => {
            const isActive = Math.abs(value - angle) < 22.5 || Math.abs(value - angle) > 337.5
            const rad = ((angle - 90) * Math.PI) / 180
            const x = 50 + 38 * Math.cos(rad)
            const y = 50 + 38 * Math.sin(rad)

            return (
              <button
                key={angle}
                onClick={() => handleCardinalClick(angle)}
                className={`absolute transform -translate-x-1/2 -translate-y-1/2 w-8 h-8 rounded-full text-xs font-bold transition-all ${
                  isActive
                    ? 'bg-primary-500 text-white scale-110 shadow-lg'
                    : 'bg-white text-slate-600 hover:bg-slate-100 shadow'
                }`}
                style={{
                  left: `${x}%`,
                  top: `${y}%`,
                }}
              >
                {label}
              </button>
            )
          })}

          {/* Center compass icon */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div
              className="transition-transform duration-200"
              style={{ transform: `rotate(${value}deg)` }}
            >
              <Compass className="w-12 h-12 text-primary-500" />
            </div>
          </div>
        </div>
      </div>

      {/* Direction display */}
      <div className="text-center">
        <div className="text-3xl font-bold text-slate-800">{value}°</div>
        <div className="text-sm text-slate-500">
          Wind from {getCardinalName(value)} ({value}°)
        </div>
      </div>

      {/* Slider */}
      <div className="space-y-2">
        <input
          type="range"
          min={0}
          max={359}
          value={value}
          onChange={handleSliderChange}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-slate-400">
          <span>N</span>
          <span>E</span>
          <span>S</span>
          <span>W</span>
          <span>N</span>
        </div>
      </div>

      {/* Quick select buttons */}
      <div className="grid grid-cols-4 gap-1">
        {[0, 90, 180, 270].map((angle) => (
          <button
            key={angle}
            onClick={() => handleCardinalClick(angle)}
            className={`py-1 px-2 text-xs rounded transition-colors ${
              value === angle
                ? 'bg-primary-500 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {angle}° {getCardinalName(angle)}
          </button>
        ))}
      </div>
    </div>
  )
}
