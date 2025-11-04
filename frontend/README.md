# Cattle Monitoring System - Frontend

A modern, responsive cattle monitoring dashboard built with Next.js 15, TypeScript, and Tailwind CSS.

## 🚀 Features

- **User Authentication**: Secure login and registration with HTTP-only cookies
- **Cattle Management**: Register, view, edit, and delete cattle records
- **Real-time Monitoring**: Monitor cattle eating patterns and temperature
- **Time-Range Analysis**: Filter monitoring data (Today, Last 2 Days, Last 7 Days, Last 30 Days, All Data)
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Modern UI**: Built with Radix UI components and Tailwind CSS

## 🛠 Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **UI Components**: Radix UI
- **Icons**: Lucide React
- **Charts**: Recharts
- **State Management**: React Context API (useAuth hook)
- **HTTP Client**: Fetch API with custom wrapper
- **Development Tools**: ESLint, Prettier

## 📦 Project Structure

```
frontend/
├── app/
│   ├── (auth)/              # Authentication routes
│   ├── (dashboard)/         # Dashboard routes
│   ├── components/          # React components
│   │   ├── ui/             # Reusable UI components
│   │   ├── CattleRegistrationModal.tsx
│   │   ├── CattleEditModal.tsx
│   │   ├── ChooseCowSection.tsx
│   │   ├── RecordDataSection.tsx
│   │   ├── Dashboard.tsx
│   │   └── Toast.tsx        # Notification system
│   ├── globals.css
│   ├── layout.tsx
│   ├── page.tsx
│   ├── login/page.tsx
│   └── favicon.ico
├── hooks/
│   └── use-auth.tsx         # Authentication context
├── lib/
│   ├── api.ts               # Backend API client
│   └── utils.ts
├── types/
│   └── index.ts             # TypeScript interfaces
├── public/
└── package.json
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Backend API running on http://localhost:8000

### Installation

```bash
cd frontend
npm install
npm run dev
```

Navigate to [http://localhost:3000](http://localhost:3000)

## 📝 Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run format` - Format code with Prettier

## 🔧 Configuration

### Environment Variables

Create `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend API Endpoints Used

- `POST /auth/register` - Register farmer
- `POST /auth/login` - Login farmer
- `GET /farm/cow?farmer_id={id}` - Get cattle list
- `POST /farm/cow` - Create cattle
- `PUT /farm/cow/{cow_id}` - Update cattle
- `DELETE /farm/cow/{cow_id}` - Delete cattle
- `GET /farm/sensor-data` - Get sensor readings

## 🎨 Key Components

- **Dashboard**: Main container managing cattle and monitoring sections
- **CattleRegistrationModal**: Form for adding new cattle
- **CattleEditModal**: Form for editing cattle details
- **ChooseCowSection**: Display and manage cattle list
- **RecordDataSection**: View sensor data with time-range filtering
- **LoginPage/RegistrationPage**: Authentication pages
- **Toast**: Notification system for user feedback

## � Data Flow

```
Frontend (Next.js)
  ↓
API Client (lib/api.ts)
  ↓
Backend API (FastAPI)
  ↓
PostgreSQL + MongoDB
```

## 🔒 Authentication

- HTTP-only cookie-based sessions
- Protected routes with useAuth hook
- Automatic session management
- Logout functionality

## � Responsive Design

Optimized for:
- Desktop (1024px+)
- Tablet (768px - 1023px)
- Mobile (320px - 767px)

## 🚨 Error Handling

- User-friendly error messages with Toast notifications
- Network error handling with retry logic
- Form validation feedback

## 📄 License

MIT License
