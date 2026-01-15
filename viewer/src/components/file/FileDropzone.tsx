import { useCallback, useState } from 'react'
import { Upload, FileText, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface FileDropzoneProps {
  onFileLoad: (filename: string, content: string) => void
  onError?: (message: string) => void
  className?: string
  accept?: string
}

/**
 * Dropzone component for loading circuit.md files
 */
export function FileDropzone({
  onFileLoad,
  onError,
  className,
  accept = '.md,.circuit.md',
}: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFile = useCallback(
    async (file: File) => {
      setIsLoading(true)
      setError(null)

      try {
        // Validate file type
        if (!file.name.endsWith('.md')) {
          throw new Error('Please select a .md file')
        }

        // Read file content
        const content = await file.text()

        onFileLoad(file.name, content)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load file'
        setError(message)
        onError?.(message)
      } finally {
        setIsLoading(false)
      }
    },
    [onFileLoad, onError]
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragging(false)

      const files = e.dataTransfer.files
      if (files.length > 0) {
        handleFile(files[0])
      }
    },
    [handleFile]
  )

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (files && files.length > 0) {
        handleFile(files[0])
      }
    },
    [handleFile]
  )

  return (
    <div
      className={cn(
        'relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors',
        isDragging
          ? 'border-blue-500 bg-blue-50'
          : 'border-slate-300 hover:border-slate-400',
        error && 'border-red-300 bg-red-50',
        className
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        type="file"
        accept={accept}
        onChange={handleInputChange}
        className="absolute inset-0 cursor-pointer opacity-0"
        disabled={isLoading}
      />

      {isLoading ? (
        <div className="flex flex-col items-center gap-2 text-slate-500">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-300 border-t-blue-500" />
          <span>Loading...</span>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center gap-2 text-red-500">
          <AlertCircle className="h-10 w-10" />
          <span className="text-sm">{error}</span>
          <span className="text-xs text-slate-500">Click or drop to try again</span>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2 text-slate-500">
          {isDragging ? (
            <>
              <Upload className="h-10 w-10 text-blue-500" />
              <span className="text-blue-500">Drop file here</span>
            </>
          ) : (
            <>
              <FileText className="h-10 w-10" />
              <span>Drop a .circuit.md file here</span>
              <span className="text-xs text-slate-400">or click to browse</span>
            </>
          )}
        </div>
      )}
    </div>
  )
}
