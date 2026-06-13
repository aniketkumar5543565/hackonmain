"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/store/auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle } from "lucide-react";
import TimetableUploader from "@/components/timetable/TimetableUploader";
import TimetableDisplay from "@/components/timetable/TimetableDisplay";
import { getTimetable, TimetableEntry } from "@/lib/timetable-api";
import { RefreshCw } from "lucide-react";

export default function TimetablePage() {
  const { profile } = useAuthStore();
  const [entries, setEntries] = useState<TimetableEntry[]>([]);
  const [loading, setLoading] = useState(true);

  // Check if user is Academic Admin
  const isAcademicAdmin = profile?.role === "ACADEMIC_ADMIN";

  const loadTimetable = async () => {
    setLoading(true);
    try {
      const data = await getTimetable();
      setEntries(data);
    } catch (err) {
      console.error("Failed to load timetable:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTimetable();
  }, []);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">📅 Timetable Management</h1>
        <p className="text-muted-foreground mt-2">
          View and manage your class schedule
        </p>
      </div>

      {/* Upload Section — Only for Academic Admins */}
      {isAcademicAdmin ? (
        <Card>
          <CardHeader>
            <CardTitle>Upload Timetable</CardTitle>
            <CardDescription>
              Upload a photo of the timetable. Our AI will extract and organize the classes.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <TimetableUploader
              onSuccess={(newEntries) => {
                setEntries(newEntries);
              }}
            />
          </CardContent>
        </Card>
      ) : (
        <div className="flex gap-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 p-4">
          <AlertCircle className="h-5 w-5 text-amber-700 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-amber-700 dark:text-amber-300">
            <p className="font-medium">Timetable Upload (Admin Only)</p>
            <p className="mt-1">
              Only Academic Admins can upload timetables. Contact your academic office to
              manage the schedule.
            </p>
          </div>
        </div>
      )}

      {/* Display Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Your Schedule</h2>
          <Button
            variant="outline"
            size="sm"
            onClick={loadTimetable}
            disabled={loading}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
        {loading ? (
          <Card>
            <CardContent className="p-6">
              <p className="text-muted-foreground text-center">Loading timetable...</p>
            </CardContent>
          </Card>
        ) : (
          <TimetableDisplay entries={entries} />
        )}
      </div>

      {/* Info */}
      <Card className="bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
        <CardHeader>
          <CardTitle className="text-base text-blue-900 dark:text-blue-200">
            💡 How it works
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-blue-800 dark:text-blue-300 space-y-2">
          <p>
            <strong>Academic Admin:</strong> Uploads timetable photos, which are automatically
            parsed and organized
          </p>
          <p>
            <strong>Students:</strong> Can view the class schedule here in an organized format
          </p>
          <p>
            The schedule also appears in your dashboard and daily AI briefings.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
