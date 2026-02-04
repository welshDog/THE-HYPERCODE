import { describe, it, expect, vi } from 'vitest'
vi.mock('../src/hypercodeLang', () => ({ setupHypercodeLanguage: () => {}, applyErrorsToModel: () => {} }))
import { render } from '@testing-library/react'
import React from 'react'
import App from '../src/App'

describe('Focus Mode visuals', () => {
  it('renders light theme', () => {
    const { container } = render(<App />)
    expect(container).toMatchSnapshot()
  })
  it('renders dark theme class', () => {
    const { container } = render(<div className="dark"><App /></div>)
    expect(container).toMatchSnapshot()
  })
})
