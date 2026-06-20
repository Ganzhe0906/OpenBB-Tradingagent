import { useState, useEffect, useRef } from 'react'
import {
  Play,
  Search,
  Terminal,
  TrendingUp,
  TrendingDown,
  Calendar,
  RefreshCw,
  BrainCircuit,
  Settings,
  Globe,
  MessageSquare,
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Circle,
  Eye,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'

export function Dashboard() {
  const [ticker, setTicker] = useState('AAPL')
  const [analysisDate, setAnalysisDate] = useState(
    new Date().toISOString().split('T')[0]
  )
  const [isRunning, setIsRunning] = useState(false)
  const [logs, setLogs] = useState<string[]>([])
  const [stockInfo, setStockInfo] = useState<{
    ticker: string
    price: number
    change: number
    change_percent: number
    source: string
  } | null>(null)
  const [lastAnalysis, setLastAnalysis] = useState<{
    ticker: string
    time: string
    status: string
  } | null>(null)

  // Macro/FinClaw State
  const [macroQuery, setMacroQuery] = useState('')
  const [isRunningMacro, setIsRunningMacro] = useState(false)
  const [macroLogs, setMacroLogs] = useState<string[]>([])
  const [lastMacroAnalysis, setLastMacroAnalysis] = useState<{
    template: string
    time: string
    status: string
  } | null>(null)

  // Stage and error progress states
  const [currentStage, setCurrentStage] = useState('')
  const [stagesProgress, setStagesProgress] = useState<any[]>([
    { id: 'market', name: '个股技术面与技术指标分析', status: 'pending' },
    { id: 'social', name: '社交舆情与市场情绪分析', status: 'pending' },
    { id: 'news', name: '核心新闻与重大事件分析', status: 'pending' },
    { id: 'fundamentals', name: '公司财务报表基本面分析', status: 'pending' },
    { id: 'debate', name: '投研团队多空对抗辩论', status: 'pending' },
    { id: 'trader', name: '交易计划制定与执行方案', status: 'pending' },
    { id: 'risk', name: '风控小组会商与PM最终裁决', status: 'pending' }
  ])
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const [macroStage, setMacroStage] = useState('')
  const [macroStagesProgress, setMacroStagesProgress] = useState<any[]>([
    { id: 'init', name: '初始化全球宏观分析环境', status: 'pending' },
    { id: 'fetch', name: '跨市场资讯检索与 FRED 数据抓取', status: 'pending' },
    { id: 'reasoning', name: 'AI 推理与全球宏观综合判定', status: 'pending' },
    { id: 'report', name: '保存并生成宏观研判报告', status: 'pending' }
  ])
  const [macroErrorMessage, setMacroErrorMessage] = useState<string | null>(null)

  const backendUrl = 'http://127.0.0.1:8000'
  const pollIntervalRef = useRef<any | null>(null)

  const scrollToBottom = () => {
    // No-op to avoid auto-scrolling when newest logs are on top
  }

  // Fetch current stock info using OpenBB / yfinance backend
  const fetchStockInfo = async () => {
    if (!ticker) return
    try {
      const formattedTicker = ticker.trim().toUpperCase()
      const res = await fetch(`${backendUrl}/api/stock-info/${formattedTicker}`)
      if (res.ok) {
        const data = await res.json()
        setStockInfo(data)
      } else {
        console.error('Failed to fetch stock info')
      }
    } catch (err) {
      console.error('Network error fetching stock info:', err)
    }
  }

  // Poll status from backend
  const checkStatus = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/status`)
      if (!res.ok) return
      const data = await res.json()

      setIsRunning(data.is_running)
      setIsRunningMacro(data.is_running_macro)

      if (data.logs && data.logs.length > 0) {
        setLogs(data.logs)
        scrollToBottom()
      }

      if (data.macro_logs && data.macro_logs.length > 0) {
        setMacroLogs(data.macro_logs)
        scrollToBottom()
      }

      if (data.last_run_time) {
        setLastAnalysis({
          ticker: data.last_run_ticker || '',
          time: new Date(data.last_run_time).toLocaleString(),
          status: data.last_run_status || '',
        })
      }

      if (data.last_macro_run_time) {
        setLastMacroAnalysis({
          template: data.last_macro_run_template || 'global_assets',
          time: new Date(data.last_macro_run_time).toLocaleString(),
          status: data.last_macro_run_status || '',
        })
      }

      setCurrentStage(data.current_stage || '')
      if (data.stages_progress && data.stages_progress.length > 0) {
        setStagesProgress(data.stages_progress)
      }
      setErrorMessage(data.error_message || null)

      setMacroStage(data.macro_stage || '')
      if (data.macro_stages_progress && data.macro_stages_progress.length > 0) {
        setMacroStagesProgress(data.macro_stages_progress)
      }
      setMacroErrorMessage(data.macro_error_message || null)

      // Stop polling when both are done
      if (!data.is_running && !data.is_running_macro && pollIntervalRef.current) {
        stopPolling()
        if (data.last_run_status === 'success') {
          setLogs((prev) => [
            ...prev,
            `[系统] 个股决策分析已完成！决策报告已生成，请前往“决策报告”页面查看。`,
          ])
          scrollToBottom()
          fetchStockInfo()
        }
        if (data.last_macro_run_status === 'success') {
          setMacroLogs((prev) => [
            ...prev,
            `[系统] 宏观研判决策分析已完成！决策报告已生成，请前往“决策报告”页面查看。`,
          ])
          scrollToBottom()
        }
      }
    } catch (err) {
      console.error('Error polling backend status:', err)
    }
  }

  const startPolling = () => {
    stopPolling()
    pollIntervalRef.current = setInterval(checkStatus, 2000)
  }

  const stopPolling = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }

  // Trigger agent pipeline
  const startAnalysis = async () => {
    if (isRunning || !ticker) return
    setIsRunning(true)
    setLogs(['[系统] 发送启动命令到后台并初始化工作流...'])
    setStockInfo(null)
    setErrorMessage(null)
    setCurrentStage('初始化工作流并启动多智能体大脑...')
    setStagesProgress([
      { id: 'market', name: '个股技术面与技术指标分析', status: 'pending' },
      { id: 'social', name: '社交舆情与市场情绪分析', status: 'pending' },
      { id: 'news', name: '核心新闻与重大事件分析', status: 'pending' },
      { id: 'fundamentals', name: '公司财务报表基本面分析', status: 'pending' },
      { id: 'debate', name: '投研团队多空对抗辩论', status: 'pending' },
      { id: 'trader', name: '交易计划制定与执行方案', status: 'pending' },
      { id: 'risk', name: '风控小组会商与PM最终裁决', status: 'pending' }
    ])

    try {
      const response = await fetch(`${backendUrl}/api/run-analysis`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ticker: ticker.trim().toUpperCase(),
          date: analysisDate,
        }),
      })

      if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.detail || '请求失败')
      }

      setLogs((prev) => [...prev, `[系统] 后台个股研判进程已成功拉起，开启日志流监控...`])
      scrollToBottom()
      startPolling()
    } catch (e: any) {
      setIsRunning(false)
      setLogs((prev) => [...prev, `[ERROR] 启动失败: ${e.message}`])
      scrollToBottom()
    }
  }

  // Trigger macro analysis pipeline
  const startMacroAnalysis = async (templateType: string) => {
    if (isRunningMacro) return
    setIsRunningMacro(true)
    setMacroLogs(['[系统] 发送启动宏观研判大脑命令并初始化工作流...'])
    setMacroErrorMessage(null)
    setMacroStage('配置就绪，启动 FinClaw 引擎...')
    setMacroStagesProgress([
      { id: 'init', name: '初始化全球宏观分析环境', status: 'running' },
      { id: 'fetch', name: '跨市场资讯检索与 FRED 数据抓取', status: 'pending' },
      { id: 'reasoning', name: 'AI 推理与全球宏观综合判定', status: 'pending' },
      { id: 'report', name: '保存并生成宏观研判报告', status: 'pending' }
    ])

    try {
      const response = await fetch(`${backendUrl}/api/run-macro-analysis`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          template_type: templateType,
          custom_query: macroQuery ? macroQuery.trim() : undefined,
        }),
      })

      if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.detail || '请求失败')
      }

      setMacroLogs((prev) => [...prev, `[系统] 后台宏观分析进程已成功拉起，开启日志流监控...`])
      scrollToBottom()
      startPolling()
    } catch (e: any) {
      setIsRunningMacro(false)
      setMacroLogs((prev) => [...prev, `[ERROR] 启动失败: ${e.message}`])
      scrollToBottom()
    }
  }

  useEffect(() => {
    // Check initial status on mount
    checkStatus()
    fetchStockInfo()

    return () => {
      stopPolling()
    }
  }, [])

  // Classify log lines for custom terminal colors
  const getLogLineStyle = (line: string) => {
    if (line.includes('[ERROR]') || line.includes('Error') || line.includes('failed')) {
      return 'text-red-400 font-semibold'
    }
    if (line.includes('[系统]') || line.includes('success') || line.includes('completed')) {
      return 'text-emerald-400 font-semibold'
    }
    if (line.includes('Initializing') || line.includes('Starting') || line.includes('economics_data') || line.includes('web_search') || line.includes('→ tool')) {
      return 'text-blue-400'
    }
    return 'text-gray-300'
  }

  return (
    <>
      {/* ===== Top Heading ===== */}
      <Header>
        <div className='flex items-center gap-2 font-semibold text-lg'>
          <BrainCircuit className='h-5 w-5 text-indigo-500 animate-pulse' />
          <span>AI Trading Brain 控制中心</span>
        </div>
        <div className='ml-auto flex items-center space-x-4'>
          <ThemeSwitch />
          <ProfileDropdown />
        </div>
      </Header>

      {/* ===== Main Content ===== */}
      <Main className='space-y-6'>
        <div className='flex flex-col gap-2 md:flex-row md:items-center md:justify-between'>
          <div>
            <h1 className='text-3xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 bg-clip-text text-transparent'>
              🤖 Dual-Engine AI 金融智能大脑
            </h1>
            <p className='text-sm text-muted-foreground mt-1'>
              融合 TradingAgents 个股共识辩论引擎与 FinClaw 全球宏观信息流抓取引擎的智能决策终端
            </p>
          </div>
          <div className='flex items-center gap-2'>
            <Badge variant='outline' className='px-3 py-1 font-medium'>
              当前环境: 本地模拟测试
            </Badge>
          </div>
        </div>

        {/* Top KPI Cards */}
        <div className='grid gap-4 sm:grid-cols-2 lg:grid-cols-4'>
          <Card className='shadow-sm hover:shadow transition-shadow'>
            <CardHeader className='flex flex-row items-center justify-between pb-2 space-y-0'>
              <CardTitle className='text-sm font-semibold text-muted-foreground'>
                分析运行状态
              </CardTitle>
              <span className='relative flex h-3 w-3'>
                <span
                  className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                    isRunning || isRunningMacro ? 'bg-amber-400' : 'bg-emerald-400'
                  }`}
                ></span>
                <span
                  className={`relative inline-flex rounded-full h-3 w-3 ${
                    isRunning || isRunningMacro ? 'bg-amber-500' : 'bg-emerald-500'
                  }`}
                ></span>
              </span>
            </CardHeader>
            <CardContent>
              <div className='text-2xl font-bold'>
                {isRunning || isRunningMacro ? '引擎研判中' : '设备空闲'}
              </div>
              <p className='text-xs text-muted-foreground mt-1'>
                {isRunning ? `正在研判个股 ${ticker.toUpperCase()}` : isRunningMacro ? '正在抓取宏观舆情' : '等待触发新决策分析'}
              </p>
            </CardContent>
          </Card>

          <Card className='shadow-sm hover:shadow transition-shadow'>
            <CardHeader className='flex flex-row items-center justify-between pb-2 space-y-0'>
              <CardTitle className='text-sm font-semibold text-muted-foreground'>
                最近分析标的
              </CardTitle>
              <BrainCircuit className='h-4 w-4 text-indigo-500' />
            </CardHeader>
            <CardContent>
              <div className='text-2xl font-bold'>
                {lastAnalysis ? lastAnalysis.ticker : '--'}
              </div>
              <p className='text-xs text-muted-foreground mt-1'>
                {lastAnalysis ? `个股: ${lastAnalysis.time}` : '暂无个股分析记录'}
              </p>
            </CardContent>
          </Card>

          <Card className='shadow-sm hover:shadow transition-shadow'>
            <CardHeader className='flex flex-row items-center justify-between pb-2 space-y-0'>
              <CardTitle className='text-sm font-semibold text-muted-foreground'>
                宏观/舆情决策
              </CardTitle>
              <Globe className='h-4 w-4 text-purple-500' />
            </CardHeader>
            <CardContent>
              <div className='text-2xl font-bold'>
                {lastMacroAnalysis ? lastMacroAnalysis.template.toUpperCase().replace('_', ' ') : '--'}
              </div>
              <p className='text-xs text-muted-foreground mt-1'>
                {lastMacroAnalysis ? `宏观: ${lastMacroAnalysis.time}` : '暂无宏观分析记录'}
              </p>
            </CardContent>
          </Card>

          <Card className='shadow-sm hover:shadow transition-shadow'>
            <CardHeader className='flex flex-row items-center justify-between pb-2 space-y-0'>
              <CardTitle className='text-sm font-semibold text-muted-foreground'>
                多智能体驱动
              </CardTitle>
              <Settings className='h-4 w-4 text-pink-500' />
            </CardHeader>
            <CardContent>
              <div className='text-2xl font-bold'>OpenBB + FinClaw</div>
              <p className='text-xs text-muted-foreground mt-1'>
                支持 FRED、yfinance、Tavily 多源融合
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Tabs for Dual-Engine Control Panels */}
        <Tabs defaultValue='stock' className='space-y-6'>
          <TabsList className='bg-slate-100 dark:bg-slate-900 p-1 rounded-xl w-fit border shadow-sm flex'>
            <TabsTrigger
              value='stock'
              className='px-5 py-2.5 rounded-lg text-sm font-semibold flex items-center gap-2 data-[state=active]:bg-white dark:data-[state=active]:bg-black data-[state=active]:shadow-md'
            >
              <BrainCircuit className='h-4 w-4 text-indigo-500' />
              个股研判控制台 (TradingAgents)
            </TabsTrigger>
            <TabsTrigger
              value='macro'
              className='px-5 py-2.5 rounded-lg text-sm font-semibold flex items-center gap-2 data-[state=active]:bg-white dark:data-[state=active]:bg-black data-[state=active]:shadow-md'
            >
              <Globe className='h-4 w-4 text-purple-500' />
              宏观与舆情研判引擎 (FinClaw)
            </TabsTrigger>
          </TabsList>

          {/* ===== 1. INDIVIDUAL STOCK ENGINE PANEL ===== */}
          <TabsContent value='stock' className='grid gap-6 md:grid-cols-12 mt-0'>
            {/* Left Panel: Controls & Quotes */}
            <div className='space-y-6 md:col-span-5'>
              {/* Control Panel Card */}
              <Card className='shadow-md border-slate-200/80 dark:border-slate-800/80'>
                <CardHeader>
                  <CardTitle className='text-lg flex items-center gap-2'>
                    🎯 智能体配置与调度
                  </CardTitle>
                  <CardDescription>配置分析股票代码与基准时区</CardDescription>
                </CardHeader>
                <CardContent className='space-y-4'>
                  <div className='space-y-2'>
                    <label className='text-xs font-semibold text-muted-foreground uppercase tracking-wider'>
                      股票交易代码 (Ticker)
                    </label>
                    <div className='flex gap-2'>
                      <Input
                        type='text'
                        value={ticker}
                        onChange={(e) => setTicker(e.target.value)}
                        placeholder='例如: AAPL, NVDA, TSLA'
                        className='uppercase font-semibold'
                        disabled={isRunning}
                        onKeyDown={(e) => e.key === 'Enter' && fetchStockInfo()}
                      />
                      <Button
                        variant='secondary'
                        onClick={fetchStockInfo}
                        disabled={isRunning || !ticker}
                      >
                        <Search className='h-4 w-4 mr-2' />
                        查询
                      </Button>
                    </div>
                  </div>

                  <div className='space-y-2'>
                    <label className='text-xs font-semibold text-muted-foreground uppercase tracking-wider'>
                      历史分析基准日期
                    </label>
                    <div className='relative flex items-center'>
                      <Input
                        type='date'
                        value={analysisDate}
                        onChange={(e) => setAnalysisDate(e.target.value)}
                        disabled={isRunning}
                        className='pl-10 font-medium'
                      />
                      <Calendar className='absolute left-3 h-4 w-4 text-muted-foreground pointer-events-none' />
                    </div>
                  </div>

                  <Button
                    className='w-full mt-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-medium py-6 shadow-md transition-all duration-300'
                    onClick={startAnalysis}
                    disabled={isRunning || !ticker}
                  >
                    {isRunning ? (
                      <>
                        <RefreshCw className='mr-2 h-4 w-4 animate-spin' />
                        正在进行智能体多方研判...
                      </>
                    ) : (
                      <>
                        <Play className='mr-2 h-4 w-4' />
                        启动智能体多方辩论与决策
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>

              {/* Stock Quote Display Card */}
              {stockInfo && (
                <Card
                  className={`shadow-md border-l-4 transition-all duration-300 ${
                    stockInfo.change >= 0
                      ? 'border-l-emerald-500 border-slate-200 dark:border-slate-800'
                      : 'border-l-rose-500 border-slate-200 dark:border-slate-800'
                  }`}
                >
                  <CardHeader className='pb-2'>
                    <div className='flex items-center justify-between'>
                      <Badge variant='outline' className='text-xs font-semibold tracking-wider'>
                        实时行情数据
                      </Badge>
                      <span className='text-[10px] text-muted-foreground font-mono'>
                        来源: {stockInfo.source}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className='flex items-baseline justify-between'>
                      <div>
                        <h2 className='text-4xl font-extrabold tracking-tight text-foreground'>
                          {stockInfo.ticker}
                        </h2>
                        <p className='text-3xl font-bold text-slate-800 dark:text-slate-100 mt-2 font-mono'>
                          ${stockInfo.price.toFixed(2)}
                        </p>
                      </div>
                      <div
                        className={`flex flex-col items-end px-3 py-2 rounded-lg font-bold ${
                          stockInfo.change >= 0
                            ? 'text-emerald-600 bg-emerald-50 dark:bg-emerald-950/30'
                            : 'text-rose-600 bg-rose-50 dark:bg-rose-950/30'
                        }`}
                      >
                        <span className='flex items-center text-lg gap-1'>
                          {stockInfo.change >= 0 ? (
                            <TrendingUp className='h-5 w-5' />
                          ) : (
                            <TrendingDown className='h-5 w-5' />
                          )}
                          {stockInfo.change >= 0 ? '+' : ''}
                          {stockInfo.change.toFixed(2)}
                        </span>
                        <span className='text-xs font-semibold'>
                          ({stockInfo.change_percent.toFixed(2)}%)
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Analysis Stage Progress Card */}
              <Card className='shadow-md border-slate-200/80 dark:border-slate-800/80'>
                <CardHeader className='pb-3'>
                  <CardTitle className='text-sm font-bold flex items-center gap-2'>
                    <Activity className='h-4 w-4 text-indigo-500 animate-pulse' />
                    个股研判进度监控
                  </CardTitle>
                  {currentStage && isRunning && (
                    <CardDescription className='text-xs text-indigo-600 dark:text-indigo-400 font-medium animate-pulse'>
                      {currentStage}
                    </CardDescription>
                  )}
                </CardHeader>
                <CardContent className='space-y-4'>
                  {errorMessage && (
                    <div className='p-3 bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/50 rounded-lg text-rose-600 dark:text-rose-400 text-xs font-mono break-all flex gap-2 items-start'>
                      <AlertTriangle className='h-4 w-4 shrink-0 mt-0.5' />
                      <div>
                        <span className='font-bold block mb-1'>研判异常终止：</span>
                        {errorMessage}
                      </div>
                    </div>
                  )}
                  
                  <div className='relative pl-4 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-[2px] before:bg-slate-100 dark:before:bg-slate-800'>
                    {stagesProgress.map((step) => {
                      let icon = <Circle className='h-4 w-4 text-slate-300 dark:text-slate-700 bg-white dark:bg-slate-900 z-10' />
                      let textClass = 'text-slate-400 dark:text-slate-500'
                      let itemClass = ''
                      
                      if (step.status === 'completed') {
                        icon = <CheckCircle2 className='h-4 w-4 text-emerald-500 bg-white dark:bg-slate-900 z-10' />
                        textClass = 'text-slate-700 dark:text-slate-300 font-medium'
                      } else if (step.status === 'running') {
                        icon = <RefreshCw className='h-4 w-4 text-indigo-500 animate-spin bg-white dark:bg-slate-900 z-10' />
                        textClass = 'text-indigo-600 dark:text-indigo-400 font-bold'
                        itemClass = 'scale-[1.02] transform transition-all duration-300'
                      } else if (step.status === 'failed') {
                        icon = <XCircle className='h-4 w-4 text-rose-500 bg-white dark:bg-slate-900 z-10' />
                        textClass = 'text-rose-600 dark:text-rose-400 font-semibold'
                      }
                      
                      return (
                        <div key={step.id} className={`flex items-center gap-3 text-xs ${itemClass}`}>
                          <span className='relative flex items-center justify-center -left-[23px]'>
                            {icon}
                          </span>
                          <span className={textClass}>{step.name}</span>
                        </div>
                      )
                    })}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Right Panel: Live Console Logs */}
            <div className='md:col-span-7'>
              <Card className='shadow-lg border-slate-200/80 dark:border-slate-800/80 h-full flex flex-col'>
                <CardHeader className='pb-3 flex flex-row items-center justify-between space-y-0 border-b border-slate-100 dark:border-slate-900'>
                  <div>
                    <CardTitle className='text-lg flex items-center gap-2'>
                      <Terminal className='h-5 w-5 text-indigo-500' />
                      个股决策实时日志
                    </CardTitle>
                    <CardDescription>
                      监控不同智能体(如 FundAgent, NewsAgent, RiskAgent) 的决策链路
                    </CardDescription>
                  </div>
                  <Badge
                    className={`font-semibold uppercase tracking-wider px-2.5 py-0.5 text-xs ${
                      isRunning
                        ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300'
                        : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300'
                    }`}
                  >
                    {isRunning ? 'Running' : 'Idle'}
                  </Badge>
                </CardHeader>
                <CardContent className='p-0 flex-1 flex flex-col bg-slate-950 dark:bg-black rounded-b-lg overflow-hidden min-h-[400px]'>
                  <div className='flex-1 p-4 h-[450px] overflow-y-auto font-mono text-xs leading-relaxed bg-slate-950 dark:bg-black text-slate-300'>
                    {logs.length === 0 ? (
                      <div className='text-slate-500 italic text-center mt-20 flex flex-col items-center gap-3'>
                        <Terminal className='h-8 w-8 text-slate-700 animate-pulse' />
                        <span>等待任务触发，实时日志将在这里流式展示...</span>
                      </div>
                    ) : (
                      <div className='space-y-1.5 flex flex-col'>
                        {[...logs].reverse().map((log, index) => (
                          <div
                            key={index}
                            className={`break-all whitespace-pre-wrap ${getLogLineStyle(log)}`}
                          >
                            {log}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  {logs.length > 0 && (
                    <div className='px-4 py-2 border-t border-slate-800 bg-slate-900 flex justify-between items-center text-[10px] text-slate-400 font-mono'>
                      <span>日志行数: {logs.length}</span>
                      <Button
                        variant='ghost'
                        size='sm'
                        className='h-6 text-[10px] text-slate-400 hover:text-slate-200 hover:bg-slate-800 px-2'
                        onClick={() => setLogs([])}
                      >
                        清空屏幕
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* ===== 2. MACRO AND INFORMATION ENGINE PANEL ===== */}
          <TabsContent value='macro' className='grid gap-6 md:grid-cols-12 mt-0'>
            {/* Left Panel: Macro Controls */}
            <div className='space-y-6 md:col-span-5'>
              <Card className='shadow-md border-slate-200/80 dark:border-slate-800/80'>
                <CardHeader>
                  <CardTitle className='text-lg flex items-center gap-2'>
                    <Globe className='h-5 w-5 text-purple-500' />
                    🌐 宏观决策大脑调度
                  </CardTitle>
                  <CardDescription>选择分析模板或自定义输入提问来研判全球宏观环境与资金动向</CardDescription>
                </CardHeader>
                <CardContent className='space-y-4'>
                  <div className='space-y-2'>
                    <label className='text-xs font-semibold text-muted-foreground uppercase tracking-wider'>
                      快捷研判任务模板
                    </label>
                    <div className='grid grid-cols-2 gap-2'>
                      <Button
                        type='button'
                        variant='outline'
                        className='flex flex-col items-center justify-center h-28 p-2 hover:bg-slate-50 dark:hover:bg-slate-900 border text-center transition-all gap-1.5'
                        onClick={() => startMacroAnalysis('weekly_flow')}
                        disabled={isRunningMacro}
                      >
                        <Globe className='h-5 w-5 text-indigo-500' />
                        <span className='text-xs font-bold'>跨市场资金流向</span>
                        <span className='text-[10px] text-muted-foreground leading-tight'>看过去一周全球资金的流向</span>
                      </Button>
                      <Button
                        type='button'
                        variant='outline'
                        className='flex flex-col items-center justify-center h-28 p-2 hover:bg-slate-50 dark:hover:bg-slate-900 border text-center transition-all gap-1.5'
                        onClick={() => startMacroAnalysis('daily_review')}
                        disabled={isRunningMacro}
                      >
                        <MessageSquare className='h-5 w-5 text-purple-500' />
                        <span className='text-xs font-bold'>24小时全球大势锐评</span>
                        <span className='text-[10px] text-muted-foreground leading-tight'>看过去24小时大事件各方分析</span>
                      </Button>
                      <Button
                        type='button'
                        variant='outline'
                        className='flex flex-col items-center justify-center h-28 p-2 hover:bg-slate-50 dark:hover:bg-slate-900 border text-center transition-all gap-1.5'
                        onClick={() => startMacroAnalysis('risk_quant')}
                        disabled={isRunningMacro}
                      >
                        <Activity className='h-5 w-5 text-pink-500' />
                        <span className='text-xs font-bold'>大类资产水位与风险量化</span>
                        <span className='text-[10px] text-muted-foreground leading-tight'>衡量此时此刻资产整体风险倾向</span>
                      </Button>
                      <Button
                        type='button'
                        variant='outline'
                        className='flex flex-col items-center justify-center h-28 p-2 hover:bg-slate-50 dark:hover:bg-slate-900 border text-center transition-all gap-1.5'
                        onClick={() => startMacroAnalysis('watchlist_monitor')}
                        disabled={isRunningMacro}
                      >
                        <Eye className='h-5 w-5 text-teal-500' />
                        <span className='text-xs font-bold'>自选核心资产监测</span>
                        <span className='text-[10px] text-muted-foreground leading-tight'>观察所关注核心资产最新动向</span>
                      </Button>
                    </div>
                  </div>

                  <div className='space-y-2'>
                    <label className='text-xs font-semibold text-muted-foreground uppercase tracking-wider'>
                      自定义宏观/信息流提问 (选填)
                    </label>
                    <Textarea
                      value={macroQuery}
                      onChange={(e) => setMacroQuery(e.target.value)}
                      placeholder='例如: 补充分析近期黄金过去10年的避险表现，并对美债ETF(TLT)进行判定...'
                      className='min-h-[100px] text-xs resize-none font-medium'
                      disabled={isRunningMacro}
                    />
                  </div>

                  <Button
                    className='w-full mt-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-medium py-6 shadow-md transition-all duration-300'
                    onClick={() => startMacroAnalysis('custom')}
                    disabled={isRunningMacro}
                  >
                    {isRunningMacro ? (
                      <>
                        <RefreshCw className='mr-2 h-4 w-4 animate-spin' />
                        正在运行 FinClaw 宏观推理引擎...
                      </>
                    ) : (
                      <>
                        <Play className='mr-2 h-4 w-4' />
                        执行自定义宏观分析
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>

              {/* Status display */}
              {lastMacroAnalysis && (
                <Card className='shadow-sm border-slate-200 dark:border-slate-800'>
                  <CardHeader className='pb-2'>
                    <CardTitle className='text-xs font-semibold text-muted-foreground uppercase tracking-wider'>
                      最近宏观研判记录
                    </CardTitle>
                  </CardHeader>
                  <CardContent className='text-xs font-medium space-y-1'>
                    <div>研判模板/类型: <Badge variant='secondary' className='font-bold uppercase'>{lastMacroAnalysis.template}</Badge></div>
                    <div>执行时间: {lastMacroAnalysis.time}</div>
                    <div>状态: <Badge variant={lastMacroAnalysis.status === 'success' ? 'default' : 'destructive'}>{lastMacroAnalysis.status === 'success' ? '成功' : '失败'}</Badge></div>
                  </CardContent>
                </Card>
              )}

              {/* Macro Analysis Stage Progress Card */}
              <Card className='shadow-md border-slate-200/80 dark:border-slate-800/80'>
                <CardHeader className='pb-3'>
                  <CardTitle className='text-sm font-bold flex items-center gap-2'>
                    <Activity className='h-4 w-4 text-purple-500 animate-pulse' />
                    宏观研判进度监控
                  </CardTitle>
                  {macroStage && isRunningMacro && (
                    <CardDescription className='text-xs text-purple-600 dark:text-purple-400 font-medium animate-pulse'>
                      {macroStage}
                    </CardDescription>
                  )}
                </CardHeader>
                <CardContent className='space-y-4'>
                  {macroErrorMessage && (
                    <div className='p-3 bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/50 rounded-lg text-rose-600 dark:text-rose-400 text-xs font-mono break-all flex gap-2 items-start'>
                      <AlertTriangle className='h-4 w-4 shrink-0 mt-0.5' />
                      <div>
                        <span className='font-bold block mb-1'>研判异常终止：</span>
                        {macroErrorMessage}
                      </div>
                    </div>
                  )}
                  
                  <div className='relative pl-4 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-[2px] before:bg-slate-100 dark:before:bg-slate-800'>
                    {macroStagesProgress.map((step) => {
                      let icon = <Circle className='h-4 w-4 text-slate-300 dark:text-slate-700 bg-white dark:bg-slate-900 z-10' />
                      let textClass = 'text-slate-400 dark:text-slate-500'
                      let itemClass = ''
                      
                      if (step.status === 'completed') {
                        icon = <CheckCircle2 className='h-4 w-4 text-emerald-500 bg-white dark:bg-slate-900 z-10' />
                        textClass = 'text-slate-700 dark:text-slate-300 font-medium'
                      } else if (step.status === 'running') {
                        icon = <RefreshCw className='h-4 w-4 text-purple-500 animate-spin bg-white dark:bg-slate-900 z-10' />
                        textClass = 'text-purple-600 dark:text-purple-400 font-bold'
                        itemClass = 'scale-[1.02] transform transition-all duration-300'
                      } else if (step.status === 'failed') {
                        icon = <XCircle className='h-4 w-4 text-rose-500 bg-white dark:bg-slate-900 z-10' />
                        textClass = 'text-rose-600 dark:text-rose-400 font-semibold'
                      }
                      
                      return (
                        <div key={step.id} className={`flex items-center gap-3 text-xs ${itemClass}`}>
                          <span className='relative flex items-center justify-center -left-[23px]'>
                            {icon}
                          </span>
                          <span className={textClass}>{step.name}</span>
                        </div>
                      )
                    })}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Right Panel: Live Macro Logs */}
            <div className='md:col-span-7'>
              <Card className='shadow-lg border-slate-200/80 dark:border-slate-800/80 h-full flex flex-col'>
                <CardHeader className='pb-3 flex flex-row items-center justify-between space-y-0 border-b border-slate-100 dark:border-slate-900'>
                  <div>
                    <CardTitle className='text-lg flex items-center gap-2'>
                      <Terminal className='h-5 w-5 text-purple-500' />
                      宏观决策实时日志
                    </CardTitle>
                    <CardDescription>
                      监控 FinClaw 跨市场爬网、FRED 宏观指标加载及 Agent 反思推理链条
                    </CardDescription>
                  </div>
                  <Badge
                    className={`font-semibold uppercase tracking-wider px-2.5 py-0.5 text-xs ${
                      isRunningMacro
                        ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300'
                        : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300'
                    }`}
                  >
                    {isRunningMacro ? 'Running' : 'Idle'}
                  </Badge>
                </CardHeader>
                <CardContent className='p-0 flex-1 flex flex-col bg-slate-950 dark:bg-black rounded-b-lg overflow-hidden min-h-[400px]'>
                  <div className='flex-1 p-4 h-[450px] overflow-y-auto font-mono text-xs leading-relaxed bg-slate-950 dark:bg-black text-slate-300'>
                    {macroLogs.length === 0 ? (
                      <div className='text-slate-500 italic text-center mt-20 flex flex-col items-center gap-3'>
                        <Terminal className='h-8 w-8 text-slate-700 animate-pulse' />
                        <span>等待宏观决策触发，FinClaw Agent 的推理日志将在这里流式展示...</span>
                      </div>
                    ) : (
                      <div className='space-y-1.5 flex flex-col'>
                        {[...macroLogs].reverse().map((log, index) => (
                          <div
                            key={index}
                            className={`break-all whitespace-pre-wrap ${getLogLineStyle(log)}`}
                          >
                            {log}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  {macroLogs.length > 0 && (
                    <div className='px-4 py-2 border-t border-slate-800 bg-slate-900 flex justify-between items-center text-[10px] text-slate-400 font-mono'>
                      <span>日志行数: {macroLogs.length}</span>
                      <Button
                        variant='ghost'
                        size='sm'
                        className='h-6 text-[10px] text-slate-400 hover:text-slate-200 hover:bg-slate-800 px-2'
                        onClick={() => setMacroLogs([])}
                      >
                        清空屏幕
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </Main>
    </>
  )
}
