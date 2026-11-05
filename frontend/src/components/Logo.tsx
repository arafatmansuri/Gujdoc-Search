export function Logo({ dark = false }: { dark?: boolean }) {
  return <div className={`flex items-center gap-2 text-lg font-bold tracking-tight ${dark ? 'text-[#17233b]' : 'text-white'}`}>
    <span className="grid h-7 w-7 place-items-center rounded-lg bg-[#e88d35] font-serif text-lg text-white">G</span>
    gujdoc
  </div>
}
