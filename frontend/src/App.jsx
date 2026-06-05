import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { ProtectedAdminRoute } from "./components/ProtectedAdminRoute";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AdminPackageEditorPage } from "./pages/admin/AdminPackageEditorPage";
import { AdminPackagesPage } from "./pages/admin/AdminPackagesPage";
import { Dashboard } from "./pages/admin/Dashboard";
import { Login } from "./pages/admin/Login";
import { HomePage } from "./pages/HomePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PackageDetailPage } from "./pages/PackageDetailPage";
import { PackagesPage } from "./pages/PackagesPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/packages" element={<PackagesPage />} />
        <Route path="/packages/:slug" element={<PackageDetailPage />} />
        <Route path="/admin/login" element={<Login />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="/admin/dashboard" element={<Dashboard />} />
        </Route>
        <Route
          path="/admin/packages"
          element={(
            <ProtectedAdminRoute>
              <AdminPackagesPage />
            </ProtectedAdminRoute>
          )}
        />
        <Route
          path="/admin/packages/new"
          element={(
            <ProtectedAdminRoute>
              <AdminPackageEditorPage />
            </ProtectedAdminRoute>
          )}
        />
        <Route
          path="/admin/packages/:packageId/edit"
          element={(
            <ProtectedAdminRoute>
              <AdminPackageEditorPage />
            </ProtectedAdminRoute>
          )}
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
