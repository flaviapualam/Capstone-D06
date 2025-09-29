'use client';

import { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { useToast } from './ui/use-toast';
import { Loader2, Users } from 'lucide-react';
import { useAuth } from '@/hooks/use-auth';

interface LoginPageProps {
  onShowRegistration: () => void;
}

export default function LoginPage({ onShowRegistration }: LoginPageProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const { login, forgotPassword } = useAuth();
  const { toast } = useToast();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await login(email, password);
      toast({
        title: "Login successful",
        description: "Welcome back!",
      });
    } catch (error) {
      console.error('Login error:', error);
      toast({
        title: "Login failed",
        description: error instanceof Error ? error.message : "Please check your credentials",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      toast({
        title: "Email required",
        description: "Please enter your email address first.",
        variant: "destructive",
      });
      return;
    }

    try {
      await forgotPassword(email);
      toast({
        title: "Password reset sent",
        description: "Check your email for password reset instructions.",
      });
      setShowForgotPassword(false);
    } catch (error) {
      console.error('Forgot password error:', error);
      toast({
        title: "Error",
        description: "Failed to send password reset email.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-green-50 to-blue-50">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="text-center space-y-4">
          <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
            <Users className="w-8 h-8 text-green-600" />
          </div>
          <div>
            <CardTitle className="text-2xl font-bold text-gray-900">
              Cattle Farm Management
            </CardTitle>
            <CardDescription className="text-gray-600">
              {showForgotPassword ? 'Reset your password' : 'Sign in to your account'}
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={showForgotPassword ? handleForgotPassword : handleLogin} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="admin@farm.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full"
              />
            </div>
            {!showForgotPassword && (
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="password123"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full"
                />
              </div>
            )}
            <Button 
              type="submit" 
              className="w-full bg-green-600 hover:bg-green-700"
              disabled={loading}
            >
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {showForgotPassword ? 'Send Reset Link' : 'Sign In'}
            </Button>
          </form>
          <div className="mt-4 text-center space-y-2">
            {!showForgotPassword ? (
              <>
                <button
                  type="button"
                  onClick={() => setShowForgotPassword(true)}
                  className="text-sm text-green-600 hover:underline block w-full"
                >
                  Forgot your password?
                </button>
                <div className="text-sm text-gray-500">
                  Don't have an account?{' '}
                  <button
                    type="button"
                    onClick={onShowRegistration}
                    className="text-green-600 hover:underline font-medium"
                  >
                    Sign up here
                  </button>
                </div>
              </>
            ) : (
              <button
                type="button"
                onClick={() => setShowForgotPassword(false)}
                className="text-sm text-green-600 hover:underline"
              >
                Back to login
              </button>
            )}
          </div>
          <div className="mt-4 p-3 bg-gray-50 rounded text-sm text-gray-600">
            <strong>Demo credentials:</strong><br />
            Email: admin@farm.com<br />
            Password: password123
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
