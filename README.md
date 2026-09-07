# Card Collection & Grading Tracker v1

Features:
- Collection inventory
- Front/back card photo upload
- Best-effort automatic centering measurement
- Estimated PSA grade
- Estimated BGS grade and Black Label likelihood
- Manual corners, edges, surface sub-scores
- PSA/BGS/CGC submission status
- Certification and actual grade tracking
- Purchase price, grading fees, market value

Important: photo grading is only an estimate and is not affiliated with or guaranteed by PSA, BGS, or CGC.

## Railway
1. Upload the project to GitHub.
2. Deploy the repo to Railway; Dockerfile is included.
3. Add a Railway persistent volume mounted at `/app/data` so the database survives redeploys.
4. For permanent photo storage, also use persistent storage for `/app/app/static/uploads`, or later upgrade to object storage.
5. Generate a public domain.

## Best photo setup
- Card flat
- Camera directly overhead
- Entire card visible
- Even lighting
- Avoid glare/sleeve reflections
