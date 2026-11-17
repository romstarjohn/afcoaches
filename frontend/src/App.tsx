import { createBrowserRouter, RouterProvider } from 'react-router'
import { UpdatePrompt } from './components/UpdatePrompt'
import { routes } from './routes'

const router = createBrowserRouter(routes)

export default function App() {
  return (
    <>
      <RouterProvider router={router} />
      <UpdatePrompt />
    </>
  )
}
