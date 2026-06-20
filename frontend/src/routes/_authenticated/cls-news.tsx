import { createFileRoute } from '@tanstack/react-router'
import { ClsNews } from '@/features/cls-news'

export const Route = createFileRoute('/_authenticated/cls-news')({
  component: ClsNews,
})
