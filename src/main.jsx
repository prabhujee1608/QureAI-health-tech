import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles.css'
import './responsive.css'
import './theme.css'
import './medical-theme.css'
import './language.css'
import './hospital.css'
import './ai-availability.css'

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
