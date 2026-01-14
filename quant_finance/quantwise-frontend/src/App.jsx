import './App.css'
import { WavyBackgroundDemo } from './component/Hero'
import { GlowingEffectDemoSecond } from './component/Grid'
import { FooterDefault } from './component/Footer'
import { NavbarDefault } from './component/Navbar'
import PortfolioAnalyzer from './pages/AnalysePortfolio'

function App() {
  return (
    <div>
      <NavbarDefault />
      <WavyBackgroundDemo />

      <div className="bg-black pt-4 -mt-16 justify-items-center pb-16">
        {/* <h1 className="pb-8 text-2xl font-bold text-white text-center m-0">
          Our Features
        </h1>
        <GlowingEffectDemoSecond /> */}
        {/* MVP QuantWise Analyzer section */}
        <PortfolioAnalyzer />
      </div>

      

      <FooterDefault />
    </div>
  )
}

export default App
