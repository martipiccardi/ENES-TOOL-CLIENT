import { useSearchParams } from 'react-router-dom'
import SearchView from './views/SearchView'
import WaveView from './views/WaveView'
import WavesForQuestion from './views/WavesForQuestion'

export default function App() {
  const [searchParams] = useSearchParams()
  const showWave = searchParams.get('show_wave')
  const showQWaves = searchParams.get('show_q_waves')

  if (showQWaves) return <WavesForQuestion />
  if (showWave) return <WaveView />
  return <SearchView />
}
