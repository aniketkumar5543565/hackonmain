"use client";

import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import Link from "next/link";
import { 
  Calendar, 
  Bell, 
  BookOpen, 
  BarChart3, 
  MessageSquare,
  Upload,
  Users,
  Clipboard,
  GraduationCap
} from "lucide-react";

// Student Features
const STUDENT_FEATURES = [
  {
    icon: Calendar,
    title: "View Timetable",
    description: "Check your class schedule",
    href: "/dashboard/timetable",
    badge: "Active",
  },
  {
    icon: BarChart3,
    title: "Attendance",
    description: "Track your attendance record",
    href: "#",
    badge: "Coming Soon",
  },
  {
    icon: Bell,
    title: "Upcoming Events",
    description: "Never miss important dates",
    href: "#",
    badge: "Coming Soon",
  },
  {
    icon: BookOpen,
    title: "Notices",
    description: "Important announcements",
    href: "#",
    badge: "Coming Soon",
  },
];

// Academic Admin Features
const ADMIN_FEATURES = [
  {
    icon: Upload,
    title: "Upload Timetable",
    description: "Upload & manage class schedules via image",
    href: "/dashboard/timetable",
    badge: "Active",
  },
  {
    icon: BarChart3,
    title: "Attendance Management",
    description: "Manage student attendance records",
    href: "#",
    badge: "Coming Soon",
  },
  {
    icon: Bell,
    title: "Create Notices",
    description: "Post announcements for students",
    href: "#",
    badge: "Coming Soon",
  },
  {
    icon: Users,
    title: "User Management",
    description: "Manage students and faculty",
    href: "#",
    badge: "Coming Soon",
  },
];

// Faculty/Professor Features
const FACULTY_FEATURES = [
  {
    icon: GraduationCap,
    title: "Create Classroom",
    description: "Set up new classroom and sections",
    href: "#",
    badge: "Coming Soon",
  },
  {
    icon: Clipboard,
    title: "Create Assignments",
    description: "Create and manage class assignments",
    href: "#",
    badge: "Coming Soon",
  },
  {
    icon: Bell,
    title: "Post Notices",
    description: "Send announcements to your classes",
    href: "#",
    badge: "Coming Soon",
  },
  {
    icon: BarChart3,
    title: "Mark Attendance",
    description: "Track student attendance",
    href: "#",
    badge: "Coming Soon",
  },
];

export default function DashboardPage() {
  const { profile, clearAuth } = useAuthStore();
  const router = useRouter();

  // Select features based on role
  let features = STUDENT_FEATURES;
  let roleTitle = "Student";
  let badgeClasses = "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800";
  let textClasses = "text-blue-900 dark:text-blue-200";
  let accentClasses = "text-blue-600 dark:text-blue-400";

  if (profile?.role === "ACADEMIC_ADMIN") {
    features = ADMIN_FEATURES;
    roleTitle = "Academic Admin";
    badgeClasses = "bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800";
    textClasses = "text-purple-900 dark:text-purple-200";
    accentClasses = "text-purple-600 dark:text-purple-400";
  } else if (profile?.role === "FACULTY") {
    features = FACULTY_FEATURES;
    roleTitle = "Professor";
    badgeClasses = "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800";
    textClasses = "text-green-900 dark:text-green-200";
    accentClasses = "text-green-600 dark:text-green-400";
  }

  async function handleLogout() {
    await supabase.auth.signOut();
    clearAuth();
    router.push("/");
  }

  const getGettingStartedText = () => {
    switch (profile?.role) {
      case "ACADEMIC_ADMIN":
        return [
          "1. <strong>Upload a timetable image</strong> in the Timetable section",
          "2. <strong>AI extracts schedules</strong> automatically",
          "3. <strong>Manage student records</strong> and announcements",
        ];
      case "FACULTY":
        return [
          "1. <strong>Create your classroom</strong> and add students",
          "2. <strong>Assign classwork</strong> to your students",
          "3. <strong>Post announcements</strong> and track attendance",
        ];
      default:
        return [
          "1. <strong>View your timetable</strong> in the Dashboard",
          "2. <strong>Check attendance</strong> records",
          "3. <strong>Receive notifications</strong> for important updates",
        ];
    }
  };

  return (
    <main className="min-h-screen p-6 bg-gradient-to-br from-background to-muted/50">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold">
              Good morning, {profile?.full_name.split(" ")[0] ?? "User"} 👋
            </h1>
            <p className="text-muted-foreground mt-1">
              <span className={`font-semibold capitalize ${accentClasses}`}>
                {roleTitle}
              </span>
              {" • "}
              <span className="text-sm">{profile?.email}</span>
            </p>
          </div>
          <Button variant="outline" onClick={handleLogout}>
            Sign Out
          </Button>
        </div>

        {/* Role Badge */}
        <Card className={`p-4 ${badgeClasses}`}>
          <p className={`${textClasses} font-medium`}>
            📌 You are logged in as <strong>{roleTitle}</strong>
          </p>
        </Card>

        {/* Features Grid */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold">Available Features</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {features.map((feature) => {
              const Icon = feature.icon;
              const isActive = feature.href !== "#";

              return (
                <Link key={feature.title} href={feature.href}>
                  <Card
                    className={`p-4 h-full transition relative ${
                      isActive
                        ? "hover:shadow-lg hover:border-primary cursor-pointer hover:scale-105"
                        : "opacity-75 cursor-not-allowed"
                    }`}
                  >
                    <div className="space-y-3">
                      <Icon className="h-6 w-6 text-primary" />
                      <div>
                        <h3 className="font-semibold text-sm">{feature.title}</h3>
                        <p className="text-xs text-muted-foreground mt-1">
                          {feature.description}
                        </p>
                      </div>
                      <div className="pt-2">
                        <span className={`text-xs px-2 py-1 rounded-full ${
                          isActive
                            ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
                            : "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300"
                        }`}>
                          {feature.badge}
                        </span>
                      </div>
                    </div>
                  </Card>
                </Link>
              );
            })}
          </div>
        </div>

        {/* Getting Started */}
        <Card className={`p-6 ${badgeClasses}`}>
          <h2 className={`font-semibold mb-4 ${textClasses}`}>
            ✨ Getting Started
          </h2>
          <ol className={`space-y-2 text-sm ${textClasses}`}>
            {getGettingStartedText().map((text, idx) => (
              <li key={idx} dangerouslySetInnerHTML={{ __html: text }} />
            ))}
          </ol>
        </Card>
      </div>
    </main>
  );
}
