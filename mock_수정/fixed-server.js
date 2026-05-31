const express = require('express')
const cors = require('cors')
const fs = require('fs')
const path = require('path')

const app = express()
const PORT = Number(process.env.PORT || 8000)
const fixturesDir = path.join(__dirname, 'fixtures')

app.use(cors())
app.use(express.json())

function fixture(name) {
  const filePath = path.join(fixturesDir, `${name}.json`)
  return JSON.parse(fs.readFileSync(filePath, 'utf8'))
}

function cloneFixture(name) {
  return JSON.parse(JSON.stringify(fixture(name)))
}

app.get('/health', (req, res) => {
  res.json({ ok: true, mode: 'fixed-mock' })
})

app.get('/student', (req, res) => {
  res.json(cloneFixture('student'))
})

app.get('/student/', (req, res) => {
  res.json(cloneFixture('student'))
})

app.patch('/student', (req, res) => {
  res.json({ ...cloneFixture('student'), ...req.body })
})

app.patch('/student/', (req, res) => {
  res.json({ ...cloneFixture('student'), ...req.body })
})

app.get('/student/progress', (req, res) => {
  res.json(cloneFixture('student-progress'))
})

app.delete('/student/feedbacks', (req, res) => {
  const progress = fixture('student-progress')
  const total = Array.isArray(progress.feedbacks) ? progress.feedbacks.length : 0
  const requested = Array.isArray(req.body?.feedback_ids) ? req.body.feedback_ids.length : 0
  const deleted = req.body?.delete_all ? total : requested
  res.json({
    deleted_count: deleted,
    remaining_count: req.body?.delete_all ? 0 : Math.max(total - deleted, 0),
  })
})

app.get('/student/school-life', (req, res) => {
  res.json(cloneFixture('school-life'))
})

app.post('/rag/scaffolding-recommendation', (req, res) => {
  res.json(cloneFixture('scaffolding-recommendation'))
})

app.get('/rag/curriculum-subjects', (req, res) => {
  res.json(cloneFixture('curriculum-subjects'))
})

app.get('/rag/curriculum-search', (req, res) => {
  const data = cloneFixture('curriculum-search')
  data.query = req.query.query || data.query
  res.json(data)
})

app.get('/rag/career-search', (req, res) => {
  const data = cloneFixture('career-search')
  data.query = req.query.query || data.query
  res.json(data)
})

app.post('/rag/career-recommendation', (req, res) => {
  res.json(cloneFixture('career-recommendation'))
})

app.use((req, res) => {
  res.status(404).json({
    detail: 'Fixed mock endpoint not found',
    method: req.method,
    path: req.path,
  })
})

app.listen(PORT, () => {
  console.log(`Fixed mock API server running at http://localhost:${PORT}`)
})
