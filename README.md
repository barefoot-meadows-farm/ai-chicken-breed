# ai-chicken-breed
AI Chicken Breed Detection

## Description
This project provides an API for detecting chicken breeds from images using both a local machine learning model and Claude Sonnet AI.

## Setup

### Installation
1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   ```
   # For Claude AI integration
   export ANTHROPIC_API_KEY=your_api_key_here

   # For Auth0 authentication
   export AUTH0_DOMAIN=your-tenant.auth0.com
   export AUTH0_API_AUDIENCE=your-api-identifier

   # For Supabase integration
   export SUPABASE_URL=your_supabase_url
   export SUPABASE_KEY=your_supabase_service_key
   ```

   Alternatively, you can create a `.env` file in the root directory with these variables.

### Supabase Configuration
1. Create a Supabase account at [supabase.com](https://supabase.com) if you don't have one
2. Create a new project in the Supabase dashboard
3. Create a table named `uploads` with the following schema:
   - `id`: uuid (primary key, default: `uuid_generate_v4()`)
   - `user_email`: text (not null)
   - `image`: text (not null) - Base64 encoded image
   - `model_type`: text (not null) - "local" or "claude"
   - `results`: jsonb (not null) - Prediction results
   - `created_at`: timestamp with time zone (not null, default: `now()`)
4. Get your Supabase URL and service key from the project settings > API
5. Set these as environment variables as shown above

### Auth0 Configuration
1. Create an Auth0 account at [auth0.com](https://auth0.com) if you don't have one
2. Create a new API in the Auth0 dashboard:
   - Name: Chicken Breed API (or any name you prefer)
   - Identifier: This will be your `AUTH0_API_AUDIENCE` value
3. Define the following permissions (scopes) for your API:
   - `read:breeds`: Read chicken breed information
   - `write:breeds`: Upload and modify chicken breed information
4. Create a new Application in the Auth0 dashboard:
   - Name: Chicken Breed Client (or any name you prefer)
   - Application Type: Regular Web Application or Single Page Application
5. In your Application settings, add the allowed callback URLs and allowed origins for your application
6. Make note of your Auth0 domain (e.g., `your-tenant.auth0.com`) for the `AUTH0_DOMAIN` environment variable

## Running the Application

### Using Python directly
```
uvicorn main:app --reload
```

### Using Docker
1. Build the Docker image:
   ```
   docker build -t ai-chicken-breed .
   ```

2. Run the Docker container:
   ```
   docker run -p 8000:8000 --env-file .env ai-chicken-breed
   ```

   Note: Make sure your `.env` file contains all the required environment variables as described in the Setup section.

3. Access the API at http://localhost:8000

## API Endpoints

All endpoints require authentication with Auth0. You'll need to include a valid JWT token in the Authorization header:
```
Authorization: Bearer your_jwt_token
```

### Local Model Prediction
```
POST /upload/
```
Upload an image to get chicken breed predictions using the local machine learning model. The image, user information, and prediction results are stored in Supabase.
- **Authentication**: Requires `write:breeds` scope
- **Returns**: Prediction results and upload ID

### Claude AI Prediction
```
POST /upload-claude/
```
Upload an image to get detailed chicken breed predictions using Claude Sonnet AI. This endpoint provides more detailed information including breed characteristics. The image, user information, and prediction results are stored in Supabase.
- **Authentication**: Requires `write:breeds` scope
- **Returns**: Prediction results and upload ID

### Hatchery Information Endpoints
- `GET /meyer/chick-breed/`: Get information about a specific breed from Meyer Hatchery
  - **Authentication**: Requires `read:breeds` scope
- `GET /hoover/chick-breed`: Get information about a specific breed from Hoover's Hatchery
  - **Authentication**: Requires `read:breeds` scope
- `GET /cackle/chick-breed`: Get information about a specific breed from Cackle Hatchery
  - **Authentication**: Requires `read:breeds` scope
- `GET /mcmurray/chick-breed`: Get information about a specific breed from McMurray Hatchery
  - **Authentication**: Requires `read:breeds` scope

### Data Collection
- `POST /scrape-chickencoop`: Start a background task to scrape chicken images from chickencoopcompany.com
  - **Authentication**: Requires `write:breeds` scope

### User Uploads
- `GET /uploads/`: Get all uploads for the authenticated user
  - **Authentication**: Requires authentication
- `GET /uploads/{upload_id}`: Get a specific upload by ID
  - **Authentication**: Requires authentication
  - Users can only access their own uploads

### Getting an Access Token
To obtain an access token for testing:

1. Use the Auth0 Management API or Auth0.js library in your client application
2. Request a token with the required scopes (`read:breeds` or `write:breeds`)
3. Include the token in your API requests as shown above
