'use client';

import { useState } from 'react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Bell } from 'lucide-react';

export default function AlertsSection() {
  const [isOpen, setIsOpen] = useState(false);
  // Simplified version - backend doesn't support alerts endpoint yet
  // TODO: Implement /farm/alerts endpoint in backend


  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="sm"
        className="relative p-2 hover:bg-gray-100"
        onClick={() => setIsOpen(!isOpen)}
        title="Alerts feature coming soon"
      >
        <Bell className="w-5 h-5 text-gray-400" />
      </Button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          <Card className="absolute right-0 top-12 w-96 shadow-lg border z-20 bg-white">
            <CardHeader className="border-b">
              <CardTitle className="text-lg flex items-center space-x-2">
                <Bell className="w-5 h-5" />
                <span>Alerts</span>
              </CardTitle>
            </CardHeader>

            <CardContent className="py-8">
              <div className="text-center text-gray-600">
                <p className="text-sm">Alerts feature coming soon</p>
                <p className="text-xs mt-2">Backend /farm/alerts endpoint needs to be implemented</p>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}