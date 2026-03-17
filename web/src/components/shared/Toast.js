import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { createContext, useCallback, useContext, useState } from "react";
const ToastContext = createContext({ toast: () => { } });
let _id = 0;
export function ToastProvider({ children }) {
    const [toasts, setToasts] = useState([]);
    const toast = useCallback((message, type = "info") => {
        const id = ++_id;
        setToasts((t) => [...t, { id, message, type }]);
        setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3500);
    }, []);
    return (_jsxs(ToastContext.Provider, { value: { toast }, children: [children, _jsx("div", { className: "toast-container", children: toasts.map((t) => (_jsx("div", { className: `toast toast-${t.type}`, children: t.message }, t.id))) })] }));
}
export function useToast() {
    return useContext(ToastContext);
}
