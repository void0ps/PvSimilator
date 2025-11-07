import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Layout } from 'antd'
import Header from './components/Layout/Header'
import Sidebar from './components/Layout/Sidebar'
import Dashboard from './pages/Dashboard'
import Systems from './pages/Systems'
import Simulations from './pages/Simulations'
import Weather from './pages/Weather'
import Analysis from './pages/Analysis'
import AlgorithmValidation from './components/AlgorithmValidation'

function App() {
  return (
    <Router>
      <Layout style={{ minHeight: '100vh' }}>
        <Header />
        <Layout>
          <Layout.Sider 
            width={320} 
            style={{ 
              background: '#fff',
              boxShadow: '2px 0 8px rgba(0,0,0,0.1)'
            }}
          >
            <Sidebar />
          </Layout.Sider>
          <Layout.Content style={{ padding: '24px', background: '#f0f2f5' }}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/systems" element={<Systems />} />
              <Route path="/simulations" element={<Simulations />} />
              <Route path="/weather" element={<Weather />} />
              <Route path="/analysis" element={<Analysis />} />
              <Route path="/validation" element={<AlgorithmValidation />} />
            </Routes>
          </Layout.Content>
        </Layout>
      </Layout>
    </Router>
  )
}

export default App