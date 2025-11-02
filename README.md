# Notion Report Download Project

This project is designed to facilitate the generation and downloading of reports from Notion. It consists of a backend built with FastAPI and a frontend developed using React.

## Project Structure

The project is organized into two main directories: `backend` and `frontend`.

### Backend

- **src/main.py**: Entry point of the FastAPI application. Sets up API routes and logging configuration.
- **src/api/health.py**: Contains the health check endpoint for the API, ensuring the service is running.
- **src/api/report.py**: Handles report-related endpoints, including generating reports and managing report downloads.
- **src/core/config.py**: Contains configuration settings for the application, such as API title, description, and logging level.
- **src/services/report/generator.py**: Contains the `ReportGenerator` class, responsible for generating reports based on the provided data.
- **requirements.txt**: Lists the dependencies required for the backend application.

### Frontend

- **src/App.tsx**: Main component of the React application, setting up the application structure and routing.
- **src/main.tsx**: Entry point for the React application, rendering the App component.
- **src/components/DownloadButton.tsx**: Exports a `DownloadButton` component that triggers the download of reports when clicked, sending pre-loaded content to the API.
- **src/services/api.ts**: Contains functions for making API calls to the backend, including the function to download reports.
- **index.html**: Main HTML file for the React application.
- **package.json**: Configuration file for npm, listing the dependencies and scripts for the frontend application.
- **tsconfig.json**: Configuration file for TypeScript, specifying compiler options and files to include in the compilation.
- **vite.config.ts**: Configuration for Vite, the build tool used for the frontend application.

## Getting Started

To get started with the project, follow these steps:

1. Clone the repository:
   ```
   git clone <repository-url>
   ```

2. Navigate to the backend directory and install the required dependencies:
   ```
   cd backend
   pip install -r requirements.txt
   ```

3. Start the backend server:
   ```
   uvicorn src.main:app --reload
   ```

4. Navigate to the frontend directory and install the required dependencies:
   ```
   cd frontend
   npm install
   ```

5. Start the frontend development server:
   ```
   npm run dev
   ```

## Usage

- Access the API at `http://localhost:8000`.
- Access the frontend application at `http://localhost:3000`.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.