import { Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
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
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
