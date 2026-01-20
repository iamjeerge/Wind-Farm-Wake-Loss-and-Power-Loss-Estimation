import { useState, useCallback } from 'react'
import { Upload, FileText, Trash2, MapPin, CheckCircle } from 'lucide-react'
import { useSimulationStore } from '../store/simulationStore'
import { layoutApi } from '../services/api'
import TurbineMap from './TurbineMap'

export default function LayoutPanel() {
  const { layout, setLayout, windDirection, setError, setIsLoading } = useSimulationStore()
  const [dragActive, setDragActive] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle')

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setDragActive(false)

      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        await handleFile(e.dataTransfer.files[0])
      }
    },
    []
  )

  const handleFileInput = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      await handleFile(e.target.files[0])
    }
  }, [])

  const handleFile = async (file: File) => {
    if (!file.name.endsWith('.csv')) {
      setError('Please upload a CSV file')
      return
    }

    setUploadStatus('uploading')
    setIsLoading(true)

    try {
      const result = await layoutApi.upload(file)
      setLayout(result)
      setUploadStatus('success')
      setTimeout(() => setUploadStatus('idle'), 3000)
    } catch (err) {
      setError('Failed to upload layout file')
      setUploadStatus('error')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleLoadSample = async () => {
    setIsLoading(true)
    try {
      const result = await layoutApi.getSample()
      setLayout(result)
    } catch (err) {
      setError('Failed to load sample layout')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleClearLayout = () => {
    setLayout(null)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Turbine Layout</h2>
          <p className="text-slate-500">Upload or configure your wind farm layout</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleLoadSample}
            className="px-4 py-2 bg-primary-100 text-primary-700 rounded-lg hover:bg-primary-200 transition-colors"
          >
            Load Sample
          </button>
          {layout && (
            <button
              onClick={handleClearLayout}
              className="px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors flex items-center gap-2"
            >
              <Trash2 className="w-4 h-4" />
              Clear
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upload Section */}
        <div className="space-y-4">
          {/* Drag & Drop Zone */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
              dragActive
                ? 'border-primary-500 bg-primary-50'
                : 'border-slate-300 hover:border-slate-400'
            }`}
          >
            <input
              type="file"
              accept=".csv"
              onChange={handleFileInput}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            
            {uploadStatus === 'uploading' ? (
              <div className="animate-pulse">
                <div className="w-12 h-12 mx-auto mb-4 bg-slate-200 rounded-full"></div>
                <p className="text-slate-500">Uploading...</p>
              </div>
            ) : uploadStatus === 'success' ? (
              <div className="text-green-600">
                <CheckCircle className="w-12 h-12 mx-auto mb-4" />
                <p className="font-medium">Upload successful!</p>
              </div>
            ) : (
              <>
                <Upload className="w-12 h-12 mx-auto mb-4 text-slate-400" />
                <p className="text-lg font-medium text-slate-700 mb-2">
                  Drop your layout CSV here
                </p>
                <p className="text-sm text-slate-500">or click to browse</p>
              </>
            )}
          </div>

          {/* CSV Format Info */}
          <div className="bg-slate-50 rounded-xl p-5">
            <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Expected CSV Format
            </h3>
            <div className="text-sm text-slate-600 space-y-2">
              <p>Your CSV should include the following columns:</p>
              <div className="bg-white rounded-lg p-3 font-mono text-xs overflow-x-auto">
                <div className="text-slate-400"># Required columns:</div>
                <div>turbine_id, latitude, longitude</div>
                <br />
                <div className="text-slate-400"># Optional columns:</div>
                <div>hub_height, rotor_diameter, rated_power_kw</div>
              </div>
              <p className="text-slate-500">
                Default hub height: 90m, rotor diameter: 126m
              </p>
            </div>
          </div>

          {/* Layout Statistics */}
          {layout && (
            <div className="bg-white rounded-xl shadow-sm border p-5">
              <h3 className="font-semibold text-slate-800 mb-4">Layout Statistics</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 rounded-lg p-3">
                  <div className="text-2xl font-bold text-primary-600">
                    {layout.turbines.length}
                  </div>
                  <div className="text-sm text-slate-500">Turbines</div>
                </div>
                <div className="bg-slate-50 rounded-lg p-3">
                  <div className="text-2xl font-bold text-primary-600">
                    {(layout.turbines.length * 3.6).toFixed(1)} MW
                  </div>
                  <div className="text-sm text-slate-500">Total Capacity</div>
                </div>
              </div>
              
              {/* Turbine Table */}
              <div className="mt-4 max-h-64 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 sticky top-0">
                    <tr>
                      <th className="text-left p-2 font-medium text-slate-600">ID</th>
                      <th className="text-left p-2 font-medium text-slate-600">Lat</th>
                      <th className="text-left p-2 font-medium text-slate-600">Lon</th>
                      <th className="text-left p-2 font-medium text-slate-600">Height</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {layout.turbines.map((t) => (
                      <tr key={t.id} className="hover:bg-slate-50">
                        <td className="p-2 font-medium">{t.id}</td>
                        <td className="p-2 text-slate-500">{t.latitude.toFixed(4)}°</td>
                        <td className="p-2 text-slate-500">{t.longitude.toFixed(4)}°</td>
                        <td className="p-2 text-slate-500">{t.hub_height}m</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Map Preview */}
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <div className="p-4 border-b flex items-center gap-2">
            <MapPin className="w-5 h-5 text-primary-500" />
            <h3 className="font-semibold text-slate-800">Layout Preview</h3>
          </div>
          <div className="h-[500px]">
            <TurbineMap layout={layout} windDirection={windDirection} />
          </div>
        </div>
      </div>
    </div>
  )
}
