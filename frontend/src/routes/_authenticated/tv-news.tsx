import { createFileRoute } from '@tanstack/react-router'
import { TvNews } from '@/features/tv-news'

export const Route = createFileRoute('/_authenticated/tv-news')({
  component: TvNews,
})
