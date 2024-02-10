// import React from "react";
// import ReactDOM from "react-dom/client";
// import { HashRouter, Routes, Route } from "react-router-dom";
// import { initializeIcons } from "@fluentui/react";

// import "./index.css";

// import Layout from "./pages/layout/Layout";
// import NoPage from "./pages/NoPage";
// import Chat from "./pages/chat/Chat";
// import { AppStateProvider } from "./state/AppProvider";

// initializeIcons();

// export default function App() {
//     return (
//         <AppStateProvider>
//             <HashRouter>
//                 <Routes>
//                     <Route path="/" element={<Layout />}>
//                         <Route index element={<Chat />} />
//                         <Route path="*" element={<NoPage />} />
//                     </Route>
//                 </Routes>
//             </HashRouter>
//         </AppStateProvider>
//     );
// }

// ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
//     <React.StrictMode>
//         <App />
//     </React.StrictMode>
// );

// Importing React libraries and ReactDOM for rendering
import React from "react";
import ReactDOM from "react-dom/client";

// Importing components and functions from react-router-dom for routing
import { HashRouter, Routes, Route } from "react-router-dom";

// Importing initializeIcons function from Fluent UI for icons initialization
import { initializeIcons } from "@fluentui/react";

// Importing global CSS styles
import "./index.css";

// Importing custom components for layout, a placeholder for no page found, and the chat feature
import Layout from "./pages/layout/Layout";
import NoPage from "./pages/NoPage";
import Chat from "./pages/chat/Chat";

// Importing AppStateProvider for global state management across the app
import { AppStateProvider } from "./state/AppProvider";

// Initialize Fluent UI icons to be used across the application
initializeIcons();

// App component definition
export default function App() {
    return (
        // Wrapping the entire app in the AppStateProvider for global state management
        <AppStateProvider>
            {/* Using HashRouter for routing based on URL hash */}
            <HashRouter>
                {/* Routes define the routing structure of the app */}
                <Routes>
                    {/* Base route '/' with Layout component */}
                    <Route path="/" element={<Layout />}>
                        {/* Index route that renders Chat component by default */}
                        <Route index element={<Chat />} />
                        {/* Wildcard route for handling undefined paths, showing NoPage component */}
                        <Route path="*" element={<NoPage />} />
                    </Route>
                </Routes>
            </HashRouter>
        </AppStateProvider>
    );
}

// Rendering the App component into the DOM
ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
        {/* App component is the root component of the application */}
        <App />
    </React.StrictMode>
);
