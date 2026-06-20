import { createFileRoute } from '@tanstack/react-router'
import { InvestmentDiary } from '@/features/investment-diary'

export const Route = createFileRoute('/_authenticated/investment-diary')({
  component: InvestmentDiary,
})
