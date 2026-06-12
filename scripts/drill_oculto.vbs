' Lanca o drill agendado SEM janela e DESTACADO do console da tarefa, pra sobreviver
' a mudancas de sessao (lock/sleep) que matavam o processo (erro 0xC000013A) no meio.
' Mesmo padrao do coletar_oculto.vbs (que nunca sofreu desse problema).
Dim sh, here
Set sh = CreateObject("WScript.Shell")
here = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
sh.Run """" & here & "drill_agendado.bat""", 0, False
