import { useState, useEffect } from 'react'
import {
  BookOpen,
  Plus,
  Trash2,
  Edit3,
  Save,
  RefreshCw,
  Brain,
  Activity,
  Sparkles,
  Eye,
  Calendar,
  MessageSquare,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Download,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { ThemeSwitch } from '@/components/theme-switch'
import { ProfileDropdown } from '@/components/profile-dropdown'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { toast } from 'sonner'

// Structured segment in the diary
interface DiarySegment {
  subject: string
  considerations: string
  operations: string
  ai_feedback: string
  observations: string
}

// Diary database record
interface DiaryRecord {
  diary_date: string
  raw_input: string
  structured_content: string // JSON representation of DiarySegment[]
  created_at: string
  updated_at: string
}

export function InvestmentDiary() {
  const [diaries, setDiaries] = useState<DiaryRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [generating, setGenerating] = useState(false)

  // Workflow Mode: 'edit' = workbench is drafting, 'review' = workbench is reviewing AI output
  const [mode, setMode] = useState<'edit' | 'review'>('edit')
  
  // Track which diary date is expanded to show raw inputs
  const [expandedRawDates, setExpandedRawDates] = useState<Record<string, boolean>>({})

  // Track which historical diary cards are collapsed/expanded
  const [expandedCardDates, setExpandedCardDates] = useState<Record<string, boolean>>({})

  const toggleCardCollapse = (date: string, defaultState: boolean) => {
    setExpandedCardDates((prev) => {
      const currentVal = prev[date] !== undefined ? prev[date] : defaultState
      return {
        ...prev,
        [date]: !currentVal,
      }
    })
  }

  // Workspace form states (Top Section)
  const [diaryDate, setDiaryDate] = useState<string>('')
  const [rawInput, setRawInput] = useState<string>('')
  const [structuredList, setStructuredList] = useState<DiarySegment[]>([])
  const [suggestion, setSuggestion] = useState<string>('')

  // Backend config
  const backendUrl = 'http://127.0.0.1:8000'

  // Get today's date in YYYY-MM-DD format
  const getTodayStr = () => {
    const d = new Date()
    const yyyy = d.getFullYear()
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    return `${yyyy}-${mm}-${dd}`
  }

  // Fetch all diaries for the bottom feed
  const fetchDiaries = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${backendUrl}/api/diaries`)
      if (res.ok) {
        const json = await res.json()
        if (json.status === 'success') {
          setDiaries(json.data)
        }
      }
    } catch (err) {
      console.error('Failed to fetch investment diaries:', err)
      toast.error('获取日记历史失败，请确认后端服务已启动')
    } finally {
      setLoading(false)
    }
  }

  // Initiate a new diary form
  const initiateNewDiary = () => {
    setDiaryDate(getTodayStr())
    setRawInput('')
    setStructuredList([])
    setSuggestion('')
    setMode('edit')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Edit an existing diary by loading it into the top workbench
  const handleEditExisting = (record: DiaryRecord) => {
    setDiaryDate(record.diary_date)
    setRawInput(record.raw_input)
    try {
      setStructuredList(JSON.parse(record.structured_content))
    } catch (e) {
      setStructuredList([])
    }
    setSuggestion('')
    setMode('edit')
    window.scrollTo({ top: 0, behavior: 'smooth' })
    toast.info(`已载入 ${record.diary_date} 的日记草稿，您可以在上方修改重新提炼`)
  }

  // Trigger AI analysis to structure raw text
  const handleGenerateDiary = async (isRegen = false) => {
    if (!rawInput.trim()) {
      toast.warning('请输入您的建模思考和操作细节')
      return
    }

    setGenerating(true)
    try {
      const body: any = {
        raw_input: rawInput,
        date: diaryDate,
      }

      if (isRegen) {
        body.suggestion = suggestion
        body.previous_structured_content = JSON.stringify(structuredList)
      }

      const res = await fetch(`${backendUrl}/api/diaries/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })

      if (res.ok) {
        const json = await res.json()
        if (json.status === 'success') {
          setStructuredList(json.data)
          setMode('review')
          toast.success(isRegen ? '重新提炼完成！' : 'AI 整理提炼已就绪，请审核')
          if (isRegen) {
            setSuggestion('')
          }
        } else {
          toast.error(`AI 提炼失败: ${json.message || '未知错误'}`)
          if (json.data) {
            setStructuredList(json.data)
            setMode('review')
          }
        }
      } else {
        const errJson = await res.json().catch(() => ({}))
        toast.error(`AI 整理请求失败: ${errJson.detail || '服务接口异常'}`)
      }
    } catch (err: any) {
      console.error('AI diary generation error:', err)
      toast.error(`请求异常: ${err.message}`)
    } finally {
      setGenerating(false)
    }
  }

  // Save the structured diary to the SQLite DB
  const handleSaveDiary = async () => {
    if (structuredList.length === 0) {
      toast.warning('没有可保存的内容，请先交由 AI 提炼整理')
      return
    }

    setSaving(true)
    try {
      const res = await fetch(`${backendUrl}/api/diaries/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          diary_date: diaryDate,
          raw_input: rawInput,
          structured_content: JSON.stringify(structuredList),
        }),
      })

      if (res.ok) {
        const json = await res.json()
        if (json.status === 'success') {
          toast.success(`日记记录保存成功 (${diaryDate})`)
          initiateNewDiary()
          // Refresh historical feed
          await fetchDiaries()
        }
      } else {
        const errJson = await res.json().catch(() => ({}))
        toast.error(`保存失败: ${errJson.detail || '未知服务器错误'}`)
      }
    } catch (err) {
      console.error('Save diary error:', err)
      toast.error('请求保存出错，请检查网络')
    } finally {
      setSaving(false)
    }
  }

  // Delete diary record
  const handleDeleteDiary = async (dateToDelete: string) => {
    if (!window.confirm(`确认要永久删除 ${dateToDelete} 的投资日记吗？`)) {
      return
    }

    try {
      const res = await fetch(`${backendUrl}/api/diaries/${dateToDelete}`, {
        method: 'DELETE',
      })
      if (res.ok) {
        toast.success(`已删除 ${dateToDelete} 的日记记录`)
        fetchDiaries()
      } else {
        toast.error('删除日记记录失败')
      }
    } catch (err) {
      console.error('Delete diary error:', err)
      toast.error('请求删除出错')
    }
  }

  // Export a diary card to Markdown file
  const handleExportMarkdown = (diary: DiaryRecord) => {
    let segments: DiarySegment[] = []
    try {
      segments = JSON.parse(diary.structured_content)
    } catch (e) {
      console.error('Failed to parse structured content during export', e)
    }

    let mdContent = `# 投资日记 - ${diary.diary_date}\n\n`
    mdContent += `## 原始输入草稿\n\`\`\`text\n${diary.raw_input || ''}\n\`\`\`\n\n`
    mdContent += `## 提炼的主题报告\n\n`

    if (segments.length === 0) {
      mdContent += `*暂无提炼的主题内容*\n`
    } else {
      segments.forEach((seg, idx) => {
        mdContent += `### 主题 ${idx + 1}: ${seg.subject || '未命名主题'}\n\n`
        
        mdContent += `#### 1. 建模思考与投资逻辑\n`
        mdContent += `${seg.considerations || '无背景记载。'}\n\n`
        
        mdContent += `#### 2. 实际操作细节\n`
        mdContent += `${seg.operations || '无操作细节。'}\n\n`
        
        mdContent += `#### 3. AI 反馈与深度研判\n`
        mdContent += `${seg.ai_feedback || '无 AI 反馈。'}\n\n`
        
        mdContent += `#### 4. 未来观察重点与点评\n`
        mdContent += `${seg.observations || '无观察点。'}\n\n`
        
        if (idx < segments.length - 1) {
          mdContent += `---\n\n`
        }
      })
    }

    // Create Blob and trigger download
    const blob = new Blob([mdContent], { type: 'text/markdown;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `投资日记_${diary.diary_date}.md`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    
    toast.success(`${diary.diary_date} 的投资日记已成功导出为 Markdown 文件`)
  }

  // Toggle raw input collapse
  const toggleRawInputCollapse = (date: string) => {
    setExpandedRawDates((prev) => ({
      ...prev,
      [date]: !prev[date],
    }))
  }

  // Initial fetch
  useEffect(() => {
    setDiaryDate(getTodayStr())
    fetchDiaries()
  }, [])

  return (
    <>
      {/* ===== Header ===== */}
      <Header>
        <div className="flex items-center gap-2 font-semibold text-lg">
          <BookOpen className="h-5 w-5 text-indigo-500" />
          <span>金融大脑 · 投资日记</span>
        </div>
        <div className="ml-auto flex items-center space-x-4">
          <ThemeSwitch />
          <ProfileDropdown />
        </div>
      </Header>

      {/* ===== Main Content ===== */}
      <Main className="space-y-8 max-w-5xl mx-auto w-full">
        {/* Title Dashboard */}
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 bg-clip-text text-transparent">
              ✍️ 个人投资建模日记
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              倾倒您零碎的建模思考与操作日志，由 AI (deepseek-v4-flash) 整理成多维度投资追踪卡片并归档
            </p>
          </div>
          {mode !== 'edit' && (
            <div className="flex items-center gap-2">
              <Button
                onClick={initiateNewDiary}
                className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-bold gap-2 text-xs shadow-sm"
                size="sm"
              >
                <Plus className="h-4 w-4" />
                写新日记
              </Button>
            </div>
          )}
        </div>

        {/* ============================================================================== */}
        {/* TOP SECTION: WORKSPACE (写日记 & AI 审核) */}
        {/* ============================================================================== */}
        <div className="space-y-6">
          {generating ? (
            /* Generating Loader State */
            <Card className="shadow-lg border-indigo-200 dark:border-indigo-950 p-12 text-center flex flex-col items-center justify-center space-y-6 min-h-[350px]">
              <div className="relative">
                <div className="absolute -inset-1 rounded-full bg-gradient-to-r from-indigo-500 to-purple-600 blur opacity-40 animate-pulse"></div>
                <div className="relative bg-white dark:bg-black p-5 rounded-full border border-indigo-500/20">
                  <Brain className="h-12 w-12 text-indigo-500 animate-bounce" />
                </div>
              </div>
              <div className="space-y-2 max-w-md">
                <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">
                  DeepSeek AI 正在整合建模日志...
                </h3>
                <p className="text-xs text-muted-foreground leading-relaxed animate-pulse">
                  我们正在将您的非结构化记录提炼为多维度交易记录卡片，并由 AI 注入投资判断力与大局观反馈，请稍候。
                </p>
              </div>
              <div className="flex items-center gap-2 text-indigo-500 text-xs font-bold bg-indigo-500/5 px-3 py-1.5 rounded-full border border-indigo-500/10">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>AI (deepseek-v4-flash) 提炼中...</span>
              </div>
            </Card>
          ) : mode === 'edit' ? (
            /* Draft Edit Mode */
            <Card className="shadow-xl border-slate-200/80 dark:border-slate-800/80 w-full">
              <CardHeader className="pb-3 border-b flex flex-row items-center justify-between flex-wrap gap-4">
                <div>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Edit3 className="text-indigo-500 h-5 w-5" />
                    写新日记 / 编辑草稿
                  </CardTitle>
                  <CardDescription>在下方自由录入关于不同标的、动作、思考的混合草稿内容</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground font-semibold">归档日期:</span>
                  <Input
                    type="date"
                    value={diaryDate}
                    onChange={(e) => setDiaryDate(e.target.value)}
                    className="w-36 h-8 text-xs font-mono"
                  />
                </div>
              </CardHeader>
              <CardContent className="p-6 space-y-5">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest block">
                    乱序日记内容录入
                  </label>
                  <Textarea
                    placeholder="今日投资思考与复盘细节。例如：
1. 考虑投资韩国股市，我觉得它的估值偏低，所以我买入了 200 股 KOSPI ETF。
2. 我又看了看美股科技股，觉得目前估值较高，选择继续观望没有进行操作。
3. 之前持有的黄金走势目前偏弱，但我觉得它的避险配置价值仍在，所以继续持有筹码不卖出..."
                    value={rawInput}
                    onChange={(e) => setRawInput(e.target.value)}
                    className="min-h-[220px] text-xs leading-relaxed font-sans placeholder:text-muted-foreground/60 resize-y"
                  />
                  <div className="text-[10px] text-muted-foreground italic flex items-center gap-1.5">
                    <AlertCircle className="h-3.5 w-3.5 text-amber-500 flex-shrink-0" />
                    <span>AI 会根据输入自动拆分为多个投资主题（如“韩国股市投资”、“美股科技股”），每个板块独立生成研判与后续观察。</span>
                  </div>
                </div>

                <div className="pt-2 border-t flex justify-end items-center gap-2">
                  <Button
                    onClick={() => handleGenerateDiary(false)}
                    disabled={!rawInput.trim()}
                    className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white font-bold gap-2 text-xs shadow-md"
                  >
                    <Sparkles className="h-4 w-4 text-amber-300 fill-amber-300" />
                    AI 提炼并生成报告
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            /* Review AI output & Audit Mode */
            <div className="space-y-6 w-full">
              <Card className="shadow-lg border-amber-500/20 bg-amber-500/[0.02]">
                <CardHeader className="py-4">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                      <CardTitle className="text-base text-slate-800 dark:text-slate-100">
                        审核 AI 提炼报告 ({diaryDate})
                      </CardTitle>
                    </div>
                    <Badge variant="outline" className="text-amber-600 border-amber-600/30 font-bold text-[10px]">
                      待审核确认
                    </Badge>
                  </div>
                  <CardDescription className="text-xs mt-1">
                    AI 成功提炼了以下投资板块。确认无误后请保存；如不满意，请在底部填写意见交由 AI 重新整理。
                  </CardDescription>
                </CardHeader>
              </Card>

              {/* Grid of Identified Subjects */}
              <div className="space-y-6">
                {structuredList.map((item, idx) => (
                  <Card key={idx} className="shadow-md border-slate-200/80 dark:border-slate-800/80 overflow-hidden">
                    <CardHeader className="bg-slate-50 dark:bg-slate-900/40 border-b py-3 flex flex-row items-center justify-between">
                      <CardTitle className="text-sm font-extrabold text-slate-800 dark:text-slate-100 flex items-center gap-2">
                        <Badge className="bg-indigo-600 hover:bg-indigo-600 text-white text-[10px]">
                          主题 {idx + 1}
                        </Badge>
                        <span className="bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent">
                          {item.subject}
                        </span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Box 1: Considerations */}
                      <div className="p-4 rounded-xl bg-purple-500/[0.02] border border-purple-500/10 space-y-2">
                        <h4 className="text-xs font-bold text-purple-600 dark:text-purple-400 flex items-center gap-1.5">
                          <Brain className="h-3.5 w-3.5" />
                          建模思考与投资逻辑
                        </h4>
                        <p className="text-xs leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
                          {item.considerations || '未提取到相关思考背景。'}
                        </p>
                      </div>

                      {/* Box 2: Operations */}
                      <div className="p-4 rounded-xl bg-indigo-500/[0.02] border border-indigo-500/10 space-y-2">
                        <h4 className="text-xs font-bold text-indigo-600 dark:text-indigo-400 flex items-center gap-1.5">
                          <Activity className="h-3.5 w-3.5" />
                          实际操作细节
                        </h4>
                        <p className="text-xs leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
                          {item.operations || '无操作记录。'}
                        </p>
                      </div>

                      {/* Box 3: AI Feedback */}
                      <div className="p-4 rounded-xl bg-emerald-500/[0.02] border border-emerald-500/10 space-y-2 md:col-span-2">
                        <h4 className="text-xs font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                          <Sparkles className="h-3.5 w-3.5 text-amber-500 fill-amber-500" />
                          AI 反馈与研判结论
                        </h4>
                        <div className="text-xs leading-relaxed text-slate-700 dark:text-slate-300 prose prose-sm dark:prose-invert max-w-none">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.ai_feedback}</ReactMarkdown>
                        </div>
                      </div>

                      {/* Box 4: Observations */}
                      <div className="p-4 rounded-xl bg-blue-500/[0.02] border border-blue-500/10 space-y-2 md:col-span-2">
                        <h4 className="text-xs font-bold text-blue-600 dark:text-blue-400 flex items-center gap-1.5">
                          <Eye className="h-3.5 w-3.5" />
                          点评与未来观察指标
                        </h4>
                        <p className="text-xs leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
                          {item.observations || '无观察要点。'}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {/* Audit Revision Feedback */}
              <Card className="shadow-lg border-indigo-100 dark:border-indigo-950">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-bold flex items-center gap-1.5">
                    <MessageSquare className="h-4 w-4 text-indigo-500" />
                    修改建议与重新提炼工作区
                  </CardTitle>
                  <CardDescription>若 AI 提炼得不准确或需要修改观点，请在此输入您的要求</CardDescription>
                </CardHeader>
                <CardContent className="p-6 space-y-4">
                  <Input
                    placeholder="修改意见示例：提醒我注意美债利率如果回升对成长股估值带来的下行冲击，并修改美股为谨慎持有..."
                    value={suggestion}
                    onChange={(e) => setSuggestion(e.target.value)}
                    className="text-xs"
                  />
                  <div className="flex justify-between items-center pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setMode('edit')}
                      className="text-xs font-semibold"
                    >
                      返回修改草稿
                    </Button>
                    <div className="flex gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={!suggestion.trim()}
                        onClick={() => handleGenerateDiary(true)}
                        className="text-xs font-semibold gap-1.5"
                      >
                        <RefreshCw className="h-3 w-3 text-indigo-500" />
                        重新整理
                      </Button>
                      <Button
                        size="sm"
                        disabled={saving}
                        onClick={handleSaveDiary}
                        className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold gap-1.5"
                      >
                        {saving ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <Save className="h-3.5 w-3.5" />
                        )}
                        确定并保存
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>

        {/* ============================================================================== */}
        {/* BOTTOM SECTION: HISTORICAL DIARIES FEED (归档记录流) */}
        {/* ============================================================================== */}
        <div className="space-y-6 pt-6 border-t border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-indigo-500" />
            <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">
              📔 历史投资日记归档 (共 {diaries.length} 篇)
            </h2>
          </div>

          {loading && diaries.length === 0 ? (
            <div className="py-20 text-center flex flex-col items-center justify-center space-y-3">
              <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
              <span className="text-xs text-muted-foreground">正在加载归档日记列表...</span>
            </div>
          ) : diaries.length === 0 ? (
            <div className="py-16 text-center text-xs text-muted-foreground italic bg-slate-50 dark:bg-slate-900/20 border border-dashed rounded-xl">
              暂无已归档的历史日记，请在上方输入草稿开始提炼！
            </div>
          ) : (
            <div className="space-y-8">
              {diaries.map((diary, index) => {
                let segments: DiarySegment[] = []
                try {
                  segments = JSON.parse(diary.structured_content)
                } catch (e) {
                  segments = []
                }
                const isExpanded = expandedRawDates[diary.diary_date] || false
                const isCardActiveExpanded = expandedCardDates[diary.diary_date] !== undefined
                  ? expandedCardDates[diary.diary_date]
                  : index === 0;

                return (
                  <Card key={diary.diary_date} className="shadow-lg border-slate-200 dark:border-slate-800 overflow-hidden w-full">
                    {/* Header: Date and Actions */}
                    <CardHeader 
                      onClick={() => toggleCardCollapse(diary.diary_date, index === 0)}
                      className="bg-slate-50/80 dark:bg-slate-900/30 py-4 border-b flex flex-row items-center justify-between flex-wrap gap-4 px-6 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-900/50 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-indigo-500" />
                        <span className="font-mono font-bold text-sm text-slate-800 dark:text-slate-100">
                          {diary.diary_date}
                        </span>
                        <Badge variant="secondary" className="text-[9px] font-bold">
                          {segments.length} 个投资主题
                        </Badge>
                        {isCardActiveExpanded ? (
                          <ChevronUp className="h-4 w-4 text-slate-400" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-slate-400" />
                        )}
                      </div>
                      <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleExportMarkdown(diary)}
                          className="h-8 text-[11px] font-semibold gap-1 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-500/5 px-2.5"
                        >
                          <Download className="h-3 w-3" />
                          导出 MD
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEditExisting(diary)}
                          className="h-8 text-[11px] font-semibold gap-1 text-indigo-500 hover:text-indigo-600 hover:bg-indigo-500/5 px-2.5"
                        >
                          <Edit3 className="h-3 w-3" />
                          载入编辑
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteDiary(diary.diary_date)}
                          className="h-8 text-[11px] font-semibold gap-1 text-red-500 hover:text-red-600 hover:bg-red-500/5 px-2.5"
                        >
                          <Trash2 className="h-3 w-3" />
                          删除
                        </Button>
                      </div>
                    </CardHeader>

                    {isCardActiveExpanded && (
                      <CardContent className="p-6 space-y-6">
                      {/* Collapsible raw draft */}
                      <div className="border border-slate-200/60 dark:border-slate-800/60 rounded-xl overflow-hidden bg-slate-50/50 dark:bg-slate-950/20">
                        <button
                          onClick={() => toggleRawInputCollapse(diary.diary_date)}
                          className="w-full flex items-center justify-between px-4 py-2.5 text-left text-[11px] font-bold text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-900/50 transition-colors"
                        >
                          <span>查看原始输入草稿文字</span>
                          {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                        </button>
                        {isExpanded && (
                          <div className="px-4 pb-4 pt-1 border-t border-slate-100 dark:border-slate-900 text-xs leading-relaxed text-slate-600 dark:text-slate-400 break-words whitespace-pre-wrap font-sans">
                            {diary.raw_input}
                          </div>
                        )}
                      </div>

                      {/* Segments Display */}
                      <div className="space-y-6">
                        {segments.map((seg, sIdx) => (
                          <div
                            key={sIdx}
                            className="border border-slate-150 dark:border-slate-800/60 rounded-xl overflow-hidden bg-white dark:bg-black"
                          >
                            <div className="bg-slate-50/40 dark:bg-slate-900/10 px-4 py-2.5 border-b font-extrabold text-xs text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                              <span className="h-1.5 w-1.5 rounded-full bg-indigo-500"></span>
                              <span>主题：{seg.subject}</span>
                            </div>
                            <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                              {/* Thoughts */}
                              <div className="p-3.5 rounded-lg bg-purple-500/[0.01] border border-purple-500/5 space-y-1.5">
                                <h5 className="text-[11px] font-extrabold text-purple-600 dark:text-purple-400 flex items-center gap-1">
                                  <Brain className="h-3 w-3" />
                                  我的建模思考与投资逻辑
                                </h5>
                                <p className="text-xs leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
                                  {seg.considerations || '无背景记载。'}
                                </p>
                              </div>

                              {/* Operations */}
                              <div className="p-3.5 rounded-lg bg-indigo-500/[0.01] border border-indigo-500/5 space-y-1.5">
                                <h5 className="text-[11px] font-extrabold text-indigo-600 dark:text-indigo-400 flex items-center gap-1">
                                  <Activity className="h-3 w-3" />
                                  实际操作细节
                                </h5>
                                <p className="text-xs leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
                                  {seg.operations || '无操作细节。'}
                                </p>
                              </div>

                              {/* AI Feedback */}
                              <div className="p-3.5 rounded-lg bg-emerald-500/[0.01] border border-emerald-500/5 space-y-1.5 md:col-span-2">
                                <h5 className="text-[11px] font-extrabold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                                  <Sparkles className="h-3 w-3 text-amber-500 fill-amber-500" />
                                  AI 反馈与深度研判
                                </h5>
                                <div className="text-xs leading-relaxed text-slate-700 dark:text-slate-300 prose prose-sm dark:prose-invert max-w-none">
                                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{seg.ai_feedback}</ReactMarkdown>
                                </div>
                              </div>

                              {/* Observations */}
                              <div className="p-3.5 rounded-lg bg-blue-500/[0.01] border border-blue-500/5 space-y-1.5 md:col-span-2">
                                <h5 className="text-[11px] font-extrabold text-blue-600 dark:text-blue-400 flex items-center gap-1">
                                  <Eye className="h-3 w-3" />
                                  未来观察重点与点评
                                </h5>
                                <p className="text-xs leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
                                  {seg.observations || '无观察点。'}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                    )}
                  </Card>
                )
              })}
            </div>
          )}
        </div>
      </Main>
    </>
  )
}
export default InvestmentDiary
