<div align="center">

<h1 style="background: linear-gradient(90deg,#a855f7,#7c3aed,#c084fc);
-webkit-background-clip: text;
color: transparent;
font-weight: 800;
font-size: 42px;">
R4M4 Content-Based Recommender System
</h1>

<p>
A movie recommendation system that compares <b>Embedding-based similarity</b> and <b>Bag-of-Words similarity</b> through an interactive web interface.
</p>

</div>

---

## R4M4 Content-Based Recommender System

<p align="center">
<img width="45%" src="https://github.com/user-attachments/assets/81abbe5e-4afe-4b39-9c4a-80a7e3237689" />
<img width="45%" src="https://github.com/user-attachments/assets/51ce1db7-d89c-4ce4-8a86-8de81285e621" />
</p>

---



This project is a **FastAPI-based movies recommender service** that exposes **two recommendation models** behind a single HTTP API:

- **Bag-of-Words (BoW) recommender** backed by a **FAISS index over reduced vectors**.
- **Embedding-based recommender** backed by a **precomputed similarity matrix**.

Both models are loaded once at startup and served through **asynchronous FastAPI routers**, which helps **reduce latency** and **increase concurrency**. The API is tested under load using **Locust**.

---

### Project structure (high level)

- **`app/main.py`**: FastAPI application, lifespan, CORS, and router registration.
- **`routes/base.py`**: Base router with a health/config endpoint.
- **`routes/data.py`**: Recommendation and movie listing endpoints.
- **`models/Recommender.py`**: Core recommender class (BoW + embeddings, FAISS search, async poster fetching).
- **`models/enums/PathEnums.py`**: Centralized paths for all assets.
- **`helpers/config.py`** and **`.env(.example)`**: Configuration and environment variables.
- **`tests/locustfile.py`**: Locust load-testing user definition.
- **`assets/`** (not tracked here but expected on disk): model artifacts and data.

---

### Data and saved artifacts

All precomputed artifacts live under the **`assets/`** directory. The project expects (at least) the following files, as referenced in `PathEnums` and the existing README:

- **`movies_df.csv`** – main movies metadata table (titles, IDs, and text fields for modeling).
- **`bow_index.faiss`** – FAISS index over reduced bag-of-words vectors.
- **`bow_dense.pkl`** – dense matrix (or array) of reduced BoW vectors, one row per movie.
- **`similarity_emb.pkl`** – precomputed similarity matrix for the embedding-based model.
- **`similarity_bow.pkl`** – (optional) BoW similarity matrix, if you keep a precomputed version in addition to the FAISS index.

> **Note**  
> The similarities for both recommenders are saved in the `assets` folder:
> - `similarity_bow.pkl`  
> - `similarity_emb.pkl`

---

### How training works

Even though the training scripts are not included in this repository, the **serving code** in `models/Recommender.py` and the asset names clearly show how each model was trained and exported.

#### 1. Bag-of-Words model with reduced vectors + FAISS index

1. **Text preprocessing**
   - Read the movies dataset from `assets/movies_df.csv`.
   - Build a text field per movie (e.g. title, genres, overview, tags).
   - Clean the text (lowercasing, punctuation removal, optional stopword removal and stemming/lemmatization).

2. **Bag-of-Words feature extraction**
   - Convert the cleaned text into a **high-dimensional sparse BoW representation** (e.g. `CountVectorizer` or `TfidfVectorizer`).
   - Optionally apply n-grams (e.g. unigrams + bigrams) to better capture phrases.

3. **Dimensionality reduction (reduced vectors)**
   - The raw BoW vectors are typically very high-dimensional and sparse.
   - Apply a **dimensionality-reduction technique** (e.g. Truncated SVD / PCA) to obtain a **dense, lower-dimensional embedding** for each movie.
   - These reduced vectors are saved as:
     - **`bow_dense.pkl`** – a dense matrix/array of shape \([n\_movies, d]\) containing the reduced BoW vectors.

4. **FAISS index creation**
   - Build a **FAISS index** (from `faiss_cpu`) over the reduced BoW vectors.
   - This index supports very fast **approximate nearest-neighbor search**, which is ideal for large catalogs.
   - The index is serialized and saved as:
     - **`bow_index.faiss`**

5. **(Optional) Similarity matrix for BoW**
   - Optionally, compute a full **pairwise similarity matrix** between movies based on the reduced BoW vectors.
   - Save the result as:
     - **`similarity_bow.pkl`**

At runtime, the BoW recommender:

- Locates the query movie by its **title** in `movies_df`.
- Extracts its reduced BoW vector from `bow_dense.pkl`.
- Performs a **FAISS search** (`bow_index.faiss`) to retrieve the nearest neighbors.
- Returns the top \(k\) most similar movies as the **Bag-of-Words recommendations**.

#### 2. Embedding-based model with similarity vector

1. **Text preprocessing**
   - Use the same `movies_df.csv` and textual fields as for BoW (or a subset tailored for semantic modeling).

2. **Embedding model**
   - Each movie is encoded into a **dense embedding** using an embedding model (e.g. a transformer-based sentence embedding model).
   - This produces a matrix of embeddings of shape \([n\_movies, d_{\text{emb}}]\).

3. **Similarity computation**
   - Compute **pairwise cosine similarities** (or another similarity metric) between all movies.
   - Store the resulting **similarity matrix** as:
     - **`similarity_emb.pkl`**

At runtime, the embedding recommender:

- Locates the query movie index in `movies_df`.
- Reads a **single similarity vector** for that movie from `similarity_emb.pkl`:
  - `movie_similarity_vec = self.emb_similarity[movie_index]`
- Uses `heapq.nlargest` to efficiently retrieve the **top-k similar movies** without sorting the entire vector:
  - This gives better-than-naive \(O(n \log n)\) performance, approaching \(O(n \log k)\).

The embedding-based recommender therefore works entirely from a **single similarity vector per query**, which is very fast at inference time.

---

### How both models are integrated in the API

The **`Recommender`** class in `models/Recommender.py` integrates the two models and exposes an async interface:

- **Initialization (on app startup)**
  - Load `movies_df.csv` into a pandas DataFrame.
  - Load the **BoW FAISS index**: `bow_index.faiss`.
  - Load the **reduced BoW vectors**: `bow_dense.pkl`.
  - Load the **embedding similarity matrix**: `similarity_emb.pkl`.
  - Prepare logging and configuration.

- **Async API for recommendations**
  - `async def recommend(movie_name: str)`: orchestrates both models.
    - Calls `recommend_emb(movie_name)` and `recommend_bow(movie_name)` **concurrently**.
    - Returns a dictionary:
      - `"embdding"` – embedding-based recommendations.
      - `"bagofwords"` – BoW/FAISS-based recommendations.

  - `async def recommend_emb(movie_name: str)`:
    - Uses the **embedding similarity vector** for the given movie.
    - Retrieves the top similar movies via `heapq.nlargest`.
    - Fetches poster URLs **asynchronously** using `asyncio.gather` + `requests_async` against the TMDB API.

  - `async def recommend_bow(movie_name: str, k: int = 7)`:
    - Looks up the corresponding **reduced BoW vector** from `bow_dense.pkl`.
    - Queries the **FAISS index** (`bow_index.faiss`) to get distances and indices of the nearest neighbors.
    - Again, fetches posters **concurrently** with `asyncio.gather`.

Because each model is **async** and **poster fetching is done concurrently**, the overall latency is substantially lower than a purely sequential implementation, especially under concurrent traffic.

---

### FastAPI application and routers

#### Application setup (`app/main.py`)

- A `FastAPI` application is created with a **lifespan context manager**:
  - During startup, a single instance of `Recommender` is attached to `app.recommender`.
  - This avoids reloading models on every request.
- **CORS middleware** is enabled with permissive settings so that web clients can call the API from any origin.
- The following routers are included:
  - **`routes.base.api_router`**
  - **`routes.data.api_router`**

#### Routers and endpoints

- **Base router (`routes/base.py`)**
  - Prefix: **`/api/v1`**
  - Endpoint:
    - `GET /api/v1/`
      - Returns basic information derived from settings:
        - `APP_NAME`
        - `APP_VERSION`

- **Data router (`routes/data.py`)**
  - Prefix: **`/api/v1`**
  - Endpoints:
    - `POST /api/v1/recommend/{movie_name}` (async)
      - Retrieves recommendations from both models for the given `movie_name`.
      - Measures and prints request **latency**.
      - Response body includes:
        - `"recommendations_embd"` – embedding-based results.
        - `"recommendations_bow"` – BoW/FAISS-based results.
    - `GET /api/v1/listmovies`
      - Returns the full list of available movie titles from `Recommender.get_movies_titles()`.

#### Why async calls help latency and concurrency

- **Asynchronous endpoints** (`async def`) allow the FastAPI server to:
  - **Release the event loop** when waiting on I/O (external APIs, network, disk).
  - Serve multiple concurrent client requests efficiently.
- Within recommendation methods:
  - Poster URLs are fetched from TMDB with **`requests_async`**.
  - Calls are batched and run via `asyncio.gather`, so multiple HTTP calls happen **in parallel**.
- Combined with **router-based separation** (`/api/v1/` base vs data endpoints), this design:
  - Keeps the API organized.
  - Reduces overall latency.
  - Improves throughput under high concurrency.

---

### Configuration and environment

Configuration is handled via `pydantic-settings`:

- **`.env.example`** shows the required env vars:
  - `APP_NAME`
  - `APP_VERSION`
  - `TMDB_ACCESS_TOKEN`
- **`helpers/config.py`** defines:
  - `Settings` model (inherits from `BaseSettings`) with the fields above.
  - `get_settings()` which reads from `.env`.
- **TMDB access token**
  - `TMDB_ACCESS_TOKEN` must be a valid token so that `get_poster_url` can fetch poster paths from TMDB.

To configure the project:

1. Copy `.env.example` to `.env`.
2. Fill in the correct values, especially `TMDB_ACCESS_TOKEN`.

---

### Running the API locally

1. **Create and activate a virtual environment (optional but recommended)**  
   Example (Windows / PowerShell):
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Ensure assets exist**
   - Place the following files under `assets/`:
     - `movies_df.csv`
     - `bow_index.faiss`
     - `bow_dense.pkl`
     - `similarity_emb.pkl`
     - (optionally) `similarity_bow.pkl`

4. **Run the development server with Uvicorn**
   ```bash
   uvicorn app.main:app --reload
   ```

5. **(For deployment)**  
   The repository includes a `Procfile` that uses:
   ```bash
   web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

---

### Example API usage

Assuming the app runs on `http://localhost:8000`:

- **Check app metadata**
  ```bash
  curl http://localhost:8000/api/v1/
  ```

- **List all available movie titles**
  ```bash
  curl http://localhost:8000/api/v1/listmovies
  ```

- **Get recommendations for a specific movie (e.g. "Tangled")**
  ```bash
  curl -X POST http://localhost:8000/api/v1/recommend/Tangled
  ```

The response will contain two lists:

- `recommendations_embd` – from the embedding similarity vector.
- `recommendations_bow` – from the FAISS index over reduced BoW vectors.

---

### Load testing with Locust

The project uses **Locust** to test API performance, concurrency, and latency characteristics.

#### Locust user definition (`tests/locustfile.py`)

- Defines a `FastAPIUser` with:
  - A wait time between **1 and 3 seconds** between tasks.
  - One task calling:
    - `GET /api/v1/listmovies`
  - Another task calling:
    - `POST /api/v1/recommend/Tangled`

This simulates real-world usage where clients both browse the catalogue and fetch recommendations.

#### Installing Locust

Locust is not pinned as an active dependency in `requirements.txt` (it is commented), so install it manually:

```bash
pip install locust==2.43.3
```

#### Running the Locust test

With the FastAPI app already running on `http://localhost:8000`, execute:

```bash
locust -f tests/locustfile.py --host http://localhost:8000 --users 200 --spawn-rate 20 --run-time 5m --headless --csv results
```

This command will:

- Spawn **200 concurrent users**.
- Start them at a **spawn rate of 20 users per second**.
- Run the test for **5 minutes** (`--run-time 5m`).
- Run in **headless mode** (no web UI), ideal for CI or automated benchmarking.
- Export detailed statistics to CSV files (`--csv results`) for later analysis.

Because the API and recommender internals are **asynchronous** and use **parallel HTTP calls** to fetch poster images, the system is well-suited to handle high concurrency while keeping per-request latency low.

---

### Summary

- **Two models**:
  - BoW model with **reduced vectors + FAISS index**.
  - Embedding model with a **precomputed similarity matrix** and per-movie similarity vectors.
- **Integrated API**:
  - Single FastAPI service exposing both models via `/api/v1/recommend/{movie_name}` and `/api/v1/listmovies`.
  - Uses **routers** and **async endpoints** to structure the API and maximize concurrency.
- **Performance-tested**:
  - Locust load tests exercise both listing and recommendation endpoints using the provided run command.
