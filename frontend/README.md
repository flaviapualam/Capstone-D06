# Cattle Monitoring System

A modern, responsive cattle monitoring and management system built with Next.js 15, TypeScript, and Tailwind CSS.

## 🚀 Features

- **User Authentication**: Secure login and registration system
- **Cattle Management**: Register and manage cattle information
- **Real-time Monitoring**: Monitor cattle health, location, and activity
- **Alert System**: Automated alerts for health and safety concerns
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Modern UI**: Built with Radix UI components and Tailwind CSS

## 🛠 Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **UI Components**: Radix UI
- **Icons**: Lucide React
- **State Management**: React Context API
- **Development Tools**: ESLint, Prettier

## 📦 Project Structure

```
frontend/
├── app/                    # Next.js app directory
│   ├── api/               # API routes
│   ├── components/        # React components
│   │   ├── ui/           # Reusable UI components
│   │   ├── features/     # Feature-specific components
│   │   └── layout/       # Layout components
│   ├── globals.css       # Global styles
│   ├── layout.tsx        # Root layout
│   └── page.tsx          # Home page
├── hooks/                 # Custom React hooks
├── lib/                   # Utility functions and API client
├── types/                 # TypeScript type definitions
└── public/                # Static assets
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start the development server**
   ```bash
   npm run dev
   ```

4. **Open your browser**
   Navigate to [http://localhost:3000](http://localhost:3000)

## 📝 Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run lint:fix` - Fix ESLint errors
- `npm run type-check` - Run TypeScript type checking
- `npm run format` - Format code with Prettier
- `npm run format:check` - Check code formatting

## 🔧 Development

### Environment Variables

Create a `.env.local` file in the root directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:3000/api
```

### API Routes

The application includes mock API routes for development:

- `POST /api/auth/login` - User authentication
- `POST /api/auth/register` - User registration
- `GET /api/cattle` - Get cattle list
- `POST /api/cattle` - Create new cattle record
- `GET /api/monitoring/status` - Get cattle status
- `GET /api/monitoring/alerts` - Get alerts
- `GET /api/monitoring/sensor-data` - Get sensor readings

### Default Login Credentials

For testing purposes, use:
- **Email**: `admin@cattle-monitor.com`
- **Password**: `password`

## 🎨 UI Components

The project uses a custom component library built on top of Radix UI:

- Button
- Input
- Label
- Card
- Toast notifications

All components are fully typed and support dark mode.

## 📱 Responsive Design

The application is fully responsive and optimized for:
- Desktop (1024px+)
- Tablet (768px - 1023px)
- Mobile (320px - 767px)

## 🔒 Authentication

The app uses a context-based authentication system with:
- JWT token storage in localStorage
- Protected routes
- Automatic session management
- Logout functionality

## 🚨 Error Handling

- Comprehensive error boundaries
- User-friendly error messages
- Network error handling
- Form validation

## 🧪 Testing

To add testing to this project, you can install:

```bash
npm install --save-dev @testing-library/react @testing-library/jest-dom jest jest-environment-jsdom
```

## 📦 Production Build

To create a production build:

```bash
npm run build
npm run start
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support, please contact the development team or create an issue in the repository.
