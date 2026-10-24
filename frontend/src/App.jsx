import { useEffect, useState } from 'react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL !== undefined ? import.meta.env.VITE_API_URL : ''
const MAX_ZIP_SIZE = 10 * 1024 * 1024

function App() {
  const [projects, setProjects] = useState([])
  const [deployments, setDeployments] = useState([])
  const [apiStatus, setApiStatus] = useState('Checking...')
  const [loading, setLoading] = useState(true)
  const [loadingDeployments, setLoadingDeployments] = useState(false)
  const [deployingProjectId, setDeployingProjectId] = useState(null)
  const [uploading, setUploading] = useState(false)

  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [appType, setAppType] = useState('python')
  const [repositoryUrl, setRepositoryUrl] = useState('')

  const [selectedZip, setSelectedZip] = useState(null)
  const [uploadProjectId, setUploadProjectId] = useState('')
  const [message, setMessage] = useState('')
  const [savedZipName, setSavedZipName] = useState('')
  const [buildImages, setBuildImages] = useState({})
  const [buildLogs, setBuildLogs] = useState([])
  const [building, setBuilding] = useState(false)

  async function loadDeployments(projectList) {
    if (projectList.length === 0) {
      setDeployments([])
      return
    }

    setLoadingDeployments(true)

    try {
      const results = await Promise.all(
        projectList.map(async (project) => {
          const response = await fetch(
            `${API_URL}/projects/${project.id}/deployments`
          )

          if (!response.ok) {
            throw new Error(
              `Could not load deployments for project ${project.id}`
            )
          }

          const records = await response.json()

          return records.map((deployment) => ({
            ...deployment,
            project_name: project.name,
          }))
        })
      )

      setDeployments(
        results.flat().sort((a, b) => b.id - a.id)
      )
    } catch (error) {
      setMessage(error.message)
    } finally {
      setLoadingDeployments(false)
    }
  }

  async function loadBuilds(projectList) {
    if (projectList.length === 0) {
      setBuildImages({})
      return
    }

    try {
      const results = await Promise.all(
        projectList.map(async (project) => {
          const response = await fetch(
            `${API_URL}/projects/${project.id}/builds`
          )

          if (!response.ok) {
            throw new Error(
              `Could not load builds for project ${project.id}`
            )
          }

          const builds = await response.json()
          return [String(project.id), builds[0] || null]
        })
      )

      const nextBuilds = {}

      results.forEach(([projectId, build]) => {
        if (build) {
          nextBuilds[projectId] = build
        }
      })

      setBuildImages(nextBuilds)
    } catch (error) {
      setMessage(`Could not load saved build history: ${error.message}`)
    }
  }

  async function loadProjects() {
    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/projects`)

      if (!response.ok) {
        throw new Error('Could not load projects')
      }

      const data = await response.json()

      setProjects(data)
      setApiStatus('Connected')

      if (data.length > 0 && !uploadProjectId) {
        setUploadProjectId(String(data[0].id))
      }

      await Promise.all([
        loadDeployments(data),
        loadBuilds(data),
      ])
    } catch (error) {
      setApiStatus('Disconnected')
      setMessage(error.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let ignore = false

    async function init() {
      try {
        const response = await fetch(`${API_URL}/projects`)
        if (!response.ok) {
          throw new Error('Could not load projects')
        }
        const data = await response.json()
        if (ignore) return

        setProjects(data)
        setApiStatus('Connected')
        if (data.length > 0) {
          setUploadProjectId((prev) => prev || String(data[0].id))
        }
        await Promise.all([
          loadDeployments(data),
          loadBuilds(data),
        ])
      } catch (error) {
        if (ignore) return
        setApiStatus('Disconnected')
        setMessage(error.message)
      } finally {
        if (!ignore) {
          setLoading(false)
        }
      }
    }

    init()

    return () => {
      ignore = true
    }
  }, [])

  async function createProject(event) {
    event.preventDefault()
    setMessage('')

    try {
      const response = await fetch(`${API_URL}/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          app_type: appType,
          repository_url: repositoryUrl || null,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Could not create project')
      }

      const project = await response.json()
      const updatedProjects = [project, ...projects]

      setProjects(updatedProjects)
      setName('')
      setAppType('python')
      setRepositoryUrl('')
      setShowForm(false)
      setMessage('Project created successfully!')

      if (!uploadProjectId) {
        setUploadProjectId(String(project.id))
      }

      await Promise.all([
        loadDeployments(updatedProjects),
        loadBuilds(updatedProjects),
      ])
    } catch (error) {
      setMessage(error.message)
    }
  }

  async function deployProject(project) {
    const savedBuild = buildImages[String(project.id)]

    if (!savedBuild?.image_name) {
      setMessage(
        `Build a Docker image for ${project.name} first. Upload its ZIP, then click Build Docker image.`
      )
      return
    }

    setMessage(`Running ${savedBuild.image_name} for ${project.name}...`)
    setDeployingProjectId(project.id)

    try {
      const response = await fetch(
        `${API_URL}/projects/${project.id}/deployments?image_name=${encodeURIComponent(savedBuild.image_name)}`,
        { method: 'POST' }
      )

      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.detail || 'Could not create deployment')
      }

      setMessage(
        `Deployment #${result.id} for ${project.name}: ${result.status}. ` +
        `Open Deployment History below to view the application's output and logs.`
      )

      await loadDeployments(projects)
    } catch (error) {
      setMessage(`Deployment failed: ${error.message}`)
    } finally {
      setDeployingProjectId(null)
    }
  }

  function selectZip(event) {
    const file = event.target.files?.[0]

    setSelectedZip(null)
    setSavedZipName('')
    setBuildLogs([])
    setMessage('')

    if (!file) return

    if (!file.name.toLowerCase().endsWith('.zip')) {
      setMessage('Please select a ZIP file.')
      event.target.value = ''
      return
    }

    if (file.size > MAX_ZIP_SIZE) {
      setMessage('The ZIP file must be 10 MB or smaller.')
      event.target.value = ''
      return
    }

    if (file.size === 0) {
      setMessage('The ZIP file is empty.')
      event.target.value = ''
      return
    }

    setSelectedZip(file)
    setMessage(`${file.name} is ready to upload.`)
  }

    async function uploadProjectZip() {
    if (!selectedZip) {
      setMessage('Please select a ZIP file first.')
      return
    }

    if (!uploadProjectId) {
      setMessage('Please select a project for this upload.')
      return
    }

    setUploading(true)
    setMessage('Uploading and validating your ZIP file...')

    try {
      const formData = new FormData()
      formData.append('file', selectedZip)

      const response = await fetch(
        `${API_URL}/projects/${uploadProjectId}/upload`,
        {
          method: 'POST',
          body: formData,
        }
      )

      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.detail || 'Upload failed.')
      }

      const project = projects.find(
        (item) => String(item.id) === uploadProjectId
      )

      setSavedZipName(result.saved_name)
      setBuildLogs([])
      setMessage(
        `Upload successful for ${project?.name || `project ${uploadProjectId}`}! ` +
        `Saved as ${result.saved_name}. You can now build the Docker image.`
      )

      setSelectedZip(null)

      const input = document.getElementById('project-zip')
      if (input) input.value = ''
    } catch (error) {
      setMessage(`Upload failed: ${error.message}`)
    } finally {
      setUploading(false)
    }
  }

  async function buildUploadedProject() {
    const sourceZipName =
      savedZipName ||
      buildImages[String(uploadProjectId)]?.saved_name ||
      ''

    if (!uploadProjectId || !sourceZipName) {
      setMessage('Upload a ZIP successfully before building.')
      return
    }

    setBuilding(true)
    setMessage('Building Docker image...')
    setBuildLogs([])

    try {
      const response = await fetch(
        `${API_URL}/projects/${uploadProjectId}/build?saved_name=${encodeURIComponent(sourceZipName)}`,
        { method: 'POST' }
      )

      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.detail || 'Docker image build failed.')
      }

      setBuildLogs(result.build_logs || [])

      if (result.image) {
        setBuildImages((previous) => ({
          ...previous,
          [String(uploadProjectId)]: {
            id: result.build_id || null,
            project_id: Number(uploadProjectId),
            image_name: result.image,
            saved_name: sourceZipName,
            entrypoint: result.entrypoint || '',
            build_logs: result.build_logs || [],
            created_at: new Date().toISOString(),
          },
        }))
      }

      setMessage(result.message || 'Docker image built successfully.')
    } catch (error) {
      setMessage(`Docker build failed: ${error.message}`)
    } finally {
      setBuilding(false)
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#dashboard">
          <span className="brand-mark">CF</span>
          <span>
            Cloud<span className="brand-light">Forge</span>
          </span>
        </a>

        <p className="nav-label">WORKSPACE</p>

        <nav className="navigation">
          <a className="nav-item active" href="#dashboard">
            <span>▦</span> Overview
          </a>
          <a className="nav-item" href="#projects">
            <span>▤</span> Projects
          </a>
          <a className="nav-item" href="#upload">
            <span>↑</span> Upload project
          </a>
          <a className="nav-item" href="#deployments">
            <span>⇧</span> Deployments
          </a>
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-status">
            <span
              className={`status-dot ${
                apiStatus === 'Connected' ? 'online' : ''
              }`}
            />
            <div>
              <strong>API Status</strong>
              <small>{apiStatus}</small>
            </div>
          </div>
          <p className="sidebar-version">CLOUDFORGE · LOCAL DEV</p>
        </div>
      </aside>

      <main className="main-content" id="dashboard">
        <header className="topbar">
          <div>
            <p className="eyebrow">WORKSPACE / OVERVIEW</p>
            <h1>Dashboard</h1>
          </div>

          <div className="profile">
            <span className="profile-avatar">CF</span>
            <div>
              <strong>Developer</strong>
              <small>Local workspace</small>
            </div>
          </div>
        </header>

        <section className="welcome">
          <div>
            <span className="welcome-tag">YOUR CLOUD WORKSPACE</span>
            <h2>Build something <span>great.</span></h2>
            <p>
              Manage projects, run Docker deployments, and prepare
              applications for the cloud.
            </p>
          </div>
          <div className="welcome-symbol" aria-hidden="true">⌘</div>
        </section>

        {message && (
          <div className="notice" role="status">
            {message}
          </div>
        )}

        <section className="stats-grid">
          <article className="stat-card">
            <div className="stat-heading">
              <span>Total projects</span>
              <span className="stat-icon purple">▤</span>
            </div>
            <strong className="stat-number">{projects.length}</strong>
            <small>Projects in your workspace</small>
          </article>

          <article className="stat-card">
            <div className="stat-heading">
              <span>API connection</span>
              <span className="stat-icon green">⌁</span>
            </div>
            <strong className="stat-number status-number">
              {apiStatus}
            </strong>
            <small>FastAPI backend</small>
          </article>

          <article className="stat-card">
            <div className="stat-heading">
              <span>Deployments</span>
              <span className="stat-icon blue">⇧</span>
            </div>
            <strong className="stat-number">{deployments.length}</strong>
            <small>Deployment records</small>
          </article>
        </section>

                <section className="projects-section" id="projects">
          <div className="section-heading">
            <div>
              <p className="eyebrow">YOUR WORKSPACE</p>
              <h2>Projects</h2>
              <p className="section-description">
                Create projects and deploy their saved Docker images.
              </p>
            </div>

            <button
              className="primary-button"
              onClick={() => setShowForm(!showForm)}
            >
              <span>＋</span> New project
            </button>
          </div>

          {showForm && (
            <form className="project-form" onSubmit={createProject}>
              <h3>Create a project</h3>

              <label htmlFor="project-name">Project name</label>
              <input
                id="project-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="e.g. My Python API"
                required
              />

              <label htmlFor="app-type">Application type</label>
              <select
                id="app-type"
                value={appType}
                onChange={(event) => setAppType(event.target.value)}
              >
                <option value="python">Python</option>
                <option value="node">Node.js</option>
                <option value="react">React</option>
              </select>

              <label htmlFor="repository-url">
                Git repository URL (optional)
              </label>
              <input
                id="repository-url"
                type="url"
                value={repositoryUrl}
                onChange={(event) => setRepositoryUrl(event.target.value)}
                placeholder="https://github.com/username/project"
              />

              <div className="form-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setShowForm(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="primary-button">
                  Create project
                </button>
              </div>
            </form>
          )}

          {loading ? (
            <div className="empty-state">Loading your projects...</div>
          ) : apiStatus !== 'Connected' ? (
            <div className="empty-state">
              <span className="empty-icon">⌁</span>
              <h3>Backend connection unavailable</h3>
              <p>Start your FastAPI server, then retry the connection.</p>
              <button className="secondary-button" onClick={loadProjects}>
                Retry connection
              </button>
            </div>
          ) : projects.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">＋</span>
              <h3>Your workspace is ready</h3>
              <p>Create your first project to get started.</p>
              <button
                className="primary-button"
                onClick={() => setShowForm(true)}
              >
                Create your first project
              </button>
            </div>
          ) : (
            <div className="project-grid">
              {projects.map((project) => (
                <article className="project-card" key={project.id}>
                  <div className="project-card-top">
                    <span className="project-icon">
                      {project.app_type === 'react'
                        ? '◈'
                        : project.app_type === 'node'
                          ? '⬡'
                          : '⌘'}
                    </span>
                    <span className="project-id">ID: {project.id}</span>
                  </div>

                  <h3>{project.name}</h3>

                  <p className="project-type">
                    {(project.app_type || 'python').toUpperCase()} APPLICATION
                  </p>

                  {project.repository_url && (
                    <a
                      className="repo-link"
                      href={project.repository_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      View repository ↗
                    </a>
                  )}

                  <div className="project-card-footer">
                    <span>
                      <span className="status-dot online" /> Created
                    </span>
                    <span>Local project</span>
                  </div>

                  <div className="project-actions">
                    <button
                      className="primary-button"
                      onClick={() => deployProject(project)}
                      disabled={
                        deployingProjectId !== null ||
                        !buildImages[String(project.id)]?.image_name
                      }
                    >
                      {deployingProjectId === project.id
                        ? 'Deploying...'
                        : '⇧ Deploy'}
                    </button>
                    <span className="action-hint">
                      {buildImages[String(project.id)]?.image_name
                        ? `Built: ${buildImages[String(project.id)].image_name}`
                        : 'Upload and build this project before deploying'}
                    </span>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="projects-section" id="upload">
          <div className="section-heading">
            <div>
              <p className="eyebrow">APPLICATION SOURCE</p>
              <h2>Upload a Python project</h2>
              <p className="section-description">
                Select a ZIP archive containing your Python application.
              </p>
            </div>
          </div>

          <div className="project-form upload-panel">
            <h3>Project archive</h3>

            <p>
              Choose an existing project and select a ZIP file up to 10 MB.
            </p>

            <label htmlFor="upload-project">
              Upload to project
            </label>
            <select
              id="upload-project"
              value={uploadProjectId}
              onChange={(event) => {
                setUploadProjectId(event.target.value)
                setSavedZipName('')
                setBuildLogs([])
                setMessage('')
              }}
              disabled={projects.length === 0 || uploading || building}
            >
              <option value="">Select a project</option>
              {projects.map((project) => (
                <option key={project.id} value={String(project.id)}>
                  {project.name} (ID: {project.id})
                </option>
              ))}
            </select>

            <label htmlFor="project-zip">Python project ZIP</label>
            <input
              id="project-zip"
              type="file"
              accept=".zip,application/zip"
              onChange={selectZip}
              disabled={uploading}
            />

            {selectedZip && (
              <div className="upload-file-info">
                <strong>Selected file</strong>
                <p>{selectedZip.name}</p>
                <small>
                  {(selectedZip.size / 1024).toFixed(1)} KB
                </small>
              </div>
            )}

            <button
              type="button"
              className="primary-button"
              disabled={
                !selectedZip ||
                !uploadProjectId ||
                uploading ||
                apiStatus !== 'Connected'
              }
              onClick={uploadProjectZip}
            >
              {uploading ? 'Uploading...' : 'Upload and validate ZIP'}
            </button>

            <p className="section-description">
              The backend validates and stores the ZIP locally. Use the Docker
              build section below to create an image; building does not execute
              the uploaded application.
            </p>
          </div>
        </section>

                <section className="projects-section" id="build">
          <div className="section-heading">
            <div>
              <p className="eyebrow">DOCKER IMAGE</p>
              <h2>Build uploaded project</h2>
              <p className="section-description">
                Build an image from the ZIP uploaded to the selected project.
              </p>
            </div>
          </div>

          <div className="project-form upload-panel">
            <h3>Image build</h3>

            <p>
              <strong>Project:</strong>{' '}
              {projects.find(
                (project) => String(project.id) === uploadProjectId
              )?.name || 'Select a project in the upload section'}
            </p>

            <p className="section-description">
              <strong>Uploaded ZIP:</strong>{' '}
              {savedZipName ||
                buildImages[String(uploadProjectId)]?.saved_name ||
                'No ZIP uploaded for this project yet'}
            </p>

            <button
              type="button"
              className="primary-button"
              onClick={buildUploadedProject}
              disabled={
                building ||
                !(
                  savedZipName ||
                  buildImages[String(uploadProjectId)]?.saved_name
                ) ||
                !uploadProjectId ||
                apiStatus !== 'Connected'
              }
            >
              {building ? 'Building Docker image...' : 'Build Docker image'}
            </button>

            {buildImages[String(uploadProjectId)]?.image_name && (
              <div className="upload-file-info">
                <strong>Latest saved build</strong>
                <p>{buildImages[String(uploadProjectId)].image_name}</p>
                <small>
                  Build information is restored from PostgreSQL. The Docker
                  image itself must still exist locally.
                </small>
              </div>
            )}

            {buildLogs.length > 0 && (
              <details className="deployment-logs" open>
                <summary>View Docker build logs</summary>
                <pre>{buildLogs.join('\n')}</pre>
              </details>
            )}
          </div>
        </section>

        <section className="deployments-section" id="deployments">
          <div className="section-heading">
            <div>
              <p className="eyebrow">DEPLOYMENT HISTORY</p>
              <h2>Deployments</h2>
              <p className="section-description">
                View Docker execution results and saved logs.
              </p>
            </div>

            <button
              className="secondary-button"
              onClick={() => loadDeployments(projects)}
              disabled={loadingDeployments || loading}
            >
              {loadingDeployments ? 'Refreshing...' : '↻ Refresh'}
            </button>
          </div>

          {loadingDeployments ? (
            <div className="empty-state">Loading deployments...</div>
          ) : deployments.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">⇧</span>
              <h3>No deployments yet</h3>
              <p>
                Upload a ZIP and build its Docker image, then click Deploy on
                that project to run it locally.
              </p>
            </div>
          ) : (
            <div className="deployment-list">
              {deployments.map((deployment) => (
                <article className="deployment-card" key={deployment.id}>
                  <div className="deployment-card-header">
                    <div>
                      <h3>Deployment #{deployment.id}</h3>
                      <p>{deployment.project_name}</p>
                    </div>

                    <span
                      className={`deployment-status ${deployment.status}`}
                    >
                      {deployment.status}
                    </span>
                  </div>

                  <p className="deployment-project-id">
                    Project ID: {deployment.project_id}
                  </p>

                  <details className="deployment-logs">
                    <summary>View deployment logs</summary>
                    <pre>
                      {deployment.logs || 'No logs available yet.'}
                    </pre>
                  </details>
                </article>
              ))}
            </div>
          )}

          <p className="deployment-disclaimer">
            Deploy runs the selected project's locally built image with
            resource limits and networking disabled. Only run code you trust;
            these limits do not make arbitrary uploaded code completely safe.
            Build records are saved in PostgreSQL and restored after refresh.
            The actual image must still exist in your local Docker Engine.
          </p>
        </section>

        <footer className="footer">
          <span>Cloud Forge</span>
          <span>Built for developers · Local environment</span>
        </footer>
      </main>
    </div>
  )
}

export default App
