import React from 'react'

export default function MetricCard({ title, value, small }) {
  return (
    <div className="p-3 bg-gray-900 rounded-md shadow-sm">
      <div className="text-sm text-gray-400">{title}</div>
      <div className={`text-2xl font-bold ${small ? 'text-lg' : ''}`}>{value}</div>
    </div>
  )
}
