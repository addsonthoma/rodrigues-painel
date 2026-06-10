' Lanca o coletor agendado SEM janela visivel (oculto), pra nao piscar na TV.
' Usado pela tarefa agendada do Windows que roda a cada 10 min.
Dim sh, here
Set sh = CreateObject("WScript.Shell")
here = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
sh.Run """" & here & "coletar_agendado.bat""", 0, False
