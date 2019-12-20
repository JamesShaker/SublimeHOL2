import os
import re
import sublime
import sublime_plugin
import time

last_handle = None

class SetHolRepl(sublime_plugin.TextCommand):
    def run(self,edit):
        last_handle = lambda : self.view.run_command("cancel_build")

class OpenHolRepl(sublime_plugin.WindowCommand):
    def run(self):
        script_path = os.path.join(sublime.packages_path(),"HOL/start_terminal.sh")
        filter_path = os.path.join(sublime.packages_path(),"HOL/filter")
        try:
            file_path   = os.path.dirname(self.window.active_view().file_name())
        except Exception:
            file_path   = "/"
        self.window.run_command("terminus_open", args={"cmd":["sh",script_path,file_path,filter_path],"title":"HOL REPL","tag":"HOL",
                                                       "post_view_hooks":[["set_hol_repl"]]})

class SendHolRepl(sublime_plugin.TextCommand):
    def run(self, edit, scope="selection", action="send", prepend="", append=""):
        if scope == "selection":
            lN,cN,text = self.selected_text()
        elif scope == "lines":
            lN,cN,text = self.selected_lines()
        elif scope == "file":
            lN,cN,text = self.selected_file()
        else:
            lN,cN,text = (0,0,"")
        #Delete things off front dependent on type of selection sent
        #TACTIC HANDLING
        if prepend[-2:] == "e(":
            #Get rid of leading whitespace and keep track
            ntext = text.lstrip()
            #Whilst we have leading tactic concatenators
            while (ntext[0:2] in [r'>-',r'>|',r'>>',r'\\']) or (ntext[0:5] in ['THEN1','THENL', 'THEN ']):
                #get rid of them
                if ntext[0:2] in [r'>-',r'>|',r'>>',r'\\']:
                    ntext = ntext[2:]
                if ntext[0:5] in ['THEN1','THENL','THEN ']:
                    ntext = ntext[5:]
                #and any revealed whitespace
                ntext = ntext.lstrip()
            #Record deletion off front
            dL = len(text) - len(ntext)
            #Get rid of trailing whitespace
            ntext = ntext.rstrip()
            #Whilst we have trailing tactic concatenators
            while (ntext[-2:] in [r'>-',r'>|',r'>>',r'\\']) or (ntext[-5:] in ['THEN1','THENL']) or (ntext[-4:] == 'THEN'):
                #get rid of them
                if ntext[-2:] in [r'>-',r'>|',r'>>',r'\\']:
                    ntext = ntext[:-2]
                if ntext[-5:] in ['THEN1','THENL']:
                    ntext = ntext[:-5]
                if ntext[-4:] == 'THEN':
                    ntext = ntext[:-4]
                #and any revealed whitespace
                ntext = ntext.rstrip()
        elif prepend[-2:] == "g(":
            #find goals by either indentifying complete, or half marked terms
            matches = re.findall(r'\‘([^’]*?)\’|`([^`]*?)`',text)
            possible_goals = [t[0] for t in matches] + [t[1] for t in matches]
            if possible_goals == []:
                possible_goals = re.split('\‘|\’|`', text)
            #take the largest possible goal and find how much deleted to get it
            ntext = max(possible_goals,key=len)
            dL    = text.find(ntext)
            #augment prepend and append
            prepend += "‘"
            append = "’" + append
        #OTHER HANDLING
        else:
            dL = 0
            ntext = text
        #handle if front stuff deleted
        if dL > 0:
            #find number of lines and characters deleted
            deleted_text = text[:dL]
            deleted_lines = deleted_text.split('\n')
            nu_lines = len(deleted_lines) - 1
            nu_chars = len(deleted_lines[-1])
            #Adjust line number and character number based on deletion
            if nu_lines > 0:
                lN += nu_lines
                cN  = nu_chars
            else:
                cN -= nu_chars
        #construct location string based on line and character number (accounting for definition syntax)
        if ntext[:10] == "Definition":
            locString = "(*#loc " + str(lN - 1) + " 0 *)\n"
        else:
            locString = "(*#loc " + str(lN) + " " + str(cN) + " *)\n"

        if prepend != "" and ntext == "" and append == "":
            command = locString + prepend
        elif prepend != "" or ntext != "" or append != "":
            command = prepend + locString + ntext + append
        #strip the command of terms and strings and comments
        stripped_command = re.sub('\`\`([\w\s\S]*?)\`\`','',command)
        stripped_command = re.sub('\`([\w\s\S]*?)\`','',stripped_command)
        stripped_command = re.sub('\“([\w\s\S]*?)\”','',stripped_command)
        stripped_command = re.sub('\‘([\w\s\S]*?)\’','',stripped_command)
        stripped_command = re.sub('\"([\w\s\S]*?)\"','',stripped_command)
        stripped_command = re.sub('\(\*([\w\s\S]*?)\*\)','',stripped_command)
        stripped_command = re.sub('Theorem[^:]*?:[\w\s\S]*?Proof','',stripped_command)
        stripped_command = re.sub('Definition[^:]*?:[\w\s\S]*?Termination','',stripped_command)
        stripped_command = re.sub('Definition[^:]*?:[\w\s\S]*?End','',stripped_command)
        stripped_command = re.sub('Inductive[^:]*?:[\w\s\S]*?End','',stripped_command)
        stripped_command = re.sub('CoInductive[^:]*?:[\w\s\S]*?End','',stripped_command)
        stripped_command = re.sub('Datatype:[\w\s\S]*?End','',stripped_command)

        #get open dependencies
        open_lines       = re.findall('open ([^;]*?);',stripped_command)
        open_deps        = re.split(r"\n|\s", " ".join(open_lines))

        #get dot dependecies
        dot_deps         = re.findall('(\w*?)\.(?:.*?)',stripped_command)

        #create dependencies loading string
        deps = list(set(open_deps + dot_deps))
        dep_string = ""
        for dep in deps:
            if dep != "" and dep != "HOL_Interactive":
                dep_string += 'load "' + dep + '";\n'

        #run final command
        final_command = u"\x01" + dep_string + command + u"\x01"
        self.view.window().run_command("terminus_send_string", args={"string": final_command,"tag":"HOL"})

    def selected_text(self):
        v = self.view
        parts = [v.substr(region) for region in v.sel()]
        lN,cN = v.rowcol(min([region.a for region in v.sel()]+[region.b for region in v.sel()]))
        lN += 1
        return (lN,cN,"".join(parts))

    def selected_lines(self):
        v = self.view
        parts = []
        region_pts = []
        for sel in v.sel():
            for line in v.lines(sel):
                parts.append(v.substr(line))
                region_pts.append(line.a)
                region_pts.append(line.b)
        lN,cN = v.rowcol(min(region_pts))
        lN += 1
        return (lN,cN,"\n".join(parts))
