import { useEffect, useMemo, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polygon, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

interface Turbine {
  id: string
  latitude: number
  longitude: number
  hub_height: number
  rotor_diameter: number
}

interface TurbineLayout {
  turbines: Turbine[]
  center_lat: number
  center_lon: number
}

interface TurbineResult {
  turbine_id: string
  power_kw: number
  wake_deficit: number
  effective_wind_speed: number
}

interface TurbineMapProps {
  layout: TurbineLayout | null
  windDirection: number
  turbineResults?: TurbineResult[]
}

// Custom turbine icon
const createTurbineIcon = (powerRatio: number) => {
  // Color from green (full power) to red (low power)
  const hue = powerRatio * 120 // 0 = red, 120 = green
  const color = `hsl(${hue}, 70%, 50%)`
  
  return L.divIcon({
    className: 'turbine-marker',
    html: `
      <div style="
        width: 24px;
        height: 24px;
        background: ${color};
        border: 3px solid white;
        border-radius: 50%;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      "></div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  })
}

// Wake cone calculation
function calculateWakeCone(
  turbine: Turbine,
  windDirection: number,
  length: number = 2000 // 2km wake length
): [number, number][] {
  const lat = turbine.latitude
  const lon = turbine.longitude
  
  // Convert wind direction to radians (wind comes FROM this direction)
  const dirRad = ((windDirection + 180) * Math.PI) / 180
  
  // Wake expansion angle (typical ~7-10 degrees)
  const expansionAngle = 8 * (Math.PI / 180)
  
  // Approximate conversion: 1 degree lat ≈ 111km, 1 degree lon ≈ 111km * cos(lat)
  const latDegPerMeter = 1 / 111000
  const lonDegPerMeter = 1 / (111000 * Math.cos(lat * Math.PI / 180))
  
  // Calculate wake cone points
  const tipX = lon + length * lonDegPerMeter * Math.sin(dirRad)
  const tipY = lat + length * latDegPerMeter * Math.cos(dirRad)
  
  const leftAngle = dirRad - expansionAngle
  const rightAngle = dirRad + expansionAngle
  
  const leftX = lon + length * lonDegPerMeter * Math.sin(leftAngle)
  const leftY = lat + length * latDegPerMeter * Math.cos(leftAngle)
  
  const rightX = lon + length * lonDegPerMeter * Math.sin(rightAngle)
  const rightY = lat + length * latDegPerMeter * Math.cos(rightAngle)
  
  return [
    [lat, lon],
    [leftY, leftX],
    [tipY, tipX],
    [rightY, rightX],
  ]
}

// Component to fit map bounds
function FitBounds({ layout }: { layout: TurbineLayout | null }) {
  const map = useMap()
  
  useEffect(() => {
    if (layout && layout.turbines.length > 0) {
      const bounds = L.latLngBounds(
        layout.turbines.map((t) => [t.latitude, t.longitude])
      )
      map.fitBounds(bounds.pad(0.2))
    }
  }, [layout, map])
  
  return null
}

// Wind direction indicator
function WindIndicator({ direction }: { direction: number }) {
  const map = useMap()
  const indicatorRef = useRef<L.Control | null>(null)
  
  useEffect(() => {
    if (indicatorRef.current) {
      map.removeControl(indicatorRef.current)
    }
    
    const CustomControl = L.Control.extend({
      onAdd: () => {
        const div = L.DomUtil.create('div', 'wind-indicator')
        div.innerHTML = `
          <div style="
            background: white;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            text-align: center;
          ">
            <div style="font-size: 12px; color: #666; margin-bottom: 4px;">Wind From</div>
            <div style="
              font-size: 24px;
              transform: rotate(${direction}deg);
              display: inline-block;
            ">⬇</div>
            <div style="font-weight: bold; color: #333;">${direction}°</div>
          </div>
        `
        return div
      },
    })
    
    indicatorRef.current = new CustomControl({ position: 'topright' })
    map.addControl(indicatorRef.current)
    
    return () => {
      if (indicatorRef.current) {
        map.removeControl(indicatorRef.current)
      }
    }
  }, [direction, map])
  
  return null
}

export default function TurbineMap({ layout, windDirection, turbineResults }: TurbineMapProps) {
  // Default center (North Sea) - used when layout is null
  // const defaultCenter: [number, number] = [55.5, 3.5]
  
  const resultMap = useMemo(() => {
    const map = new Map<string, TurbineResult>()
    if (turbineResults) {
      turbineResults.forEach((r) => map.set(r.turbine_id, r))
    }
    return map
  }, [turbineResults])
  
  const maxPower = useMemo(() => {
    if (!turbineResults || turbineResults.length === 0) return 1
    return Math.max(...turbineResults.map((r) => r.power_kw))
  }, [turbineResults])
  
  if (!layout) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-100">
        <div className="text-slate-500">Loading map...</div>
      </div>
    )
  }
  
  return (
    <MapContainer
      center={[layout.center_lat, layout.center_lon]}
      zoom={12}
      className="h-full w-full"
      style={{ background: '#e2e8f0' }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      
      <FitBounds layout={layout} />
      <WindIndicator direction={windDirection} />
      
      {/* Wake cones */}
      {layout.turbines.map((turbine) => {
        const result = resultMap.get(turbine.id)
        const hasWake = result && result.wake_deficit > 0.01
        
        return (
          <Polygon
            key={`wake-${turbine.id}`}
            positions={calculateWakeCone(turbine, windDirection)}
            pathOptions={{
              color: hasWake ? '#ef4444' : '#3b82f6',
              fillColor: hasWake ? '#fca5a5' : '#93c5fd',
              fillOpacity: 0.2,
              weight: 1,
            }}
          />
        )
      })}
      
      {/* Turbine markers */}
      {layout.turbines.map((turbine) => {
        const result = resultMap.get(turbine.id)
        const powerRatio = result ? result.power_kw / maxPower : 1
        
        return (
          <Marker
            key={turbine.id}
            position={[turbine.latitude, turbine.longitude]}
            icon={createTurbineIcon(powerRatio)}
          >
            <Popup>
              <div className="text-sm">
                <div className="font-bold text-slate-800 mb-2">{turbine.id}</div>
                <div className="space-y-1 text-slate-600">
                  <div>Hub Height: {turbine.hub_height}m</div>
                  <div>Rotor Diameter: {turbine.rotor_diameter}m</div>
                  {result && (
                    <>
                      <hr className="my-2" />
                      <div className="text-green-600 font-medium">
                        Power: {(result.power_kw / 1000).toFixed(2)} MW
                      </div>
                      <div className="text-orange-600">
                        Wake Loss: {(result.wake_deficit * 100).toFixed(1)}%
                      </div>
                      <div className="text-blue-600">
                        Effective Wind: {result.effective_wind_speed.toFixed(1)} m/s
                      </div>
                    </>
                  )}
                </div>
              </div>
            </Popup>
          </Marker>
        )
      })}
    </MapContainer>
  )
}
