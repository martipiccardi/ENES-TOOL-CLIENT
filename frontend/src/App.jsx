import { useSearchParams } from 'react-router-dom'
import SearchView from './views/SearchView'
import WaveView from './views/WaveView'
import WavesForQuestion from './views/WavesForQuestion'
import VolAView from './views/VolAView'

export default function App() {
  const [searchParams] = useSearchParams()
  const showWave = searchParams.get('show_wave')
  const showQWaves = searchParams.get('show_q_waves')
  const showVolA = searchParams.get('show_vol_a')

  if (showVolA) return <VolAView />
  if (showQWaves) return <WavesForQuestion />
  if (showWave) return <WaveView />
  return <SearchView />
}
