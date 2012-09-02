#!/usr/bin/python
# License: MIT - http://opensource.org/licenses/mit-license.php
# Copyright (c) 2012 Oddstr13 <oddstr13@openshell.no>
# http://oddstr13.openshell.no/

# Example config:
# ------------------------------
# {
#   "modid"        : "mod_UrbanCraftCoins",
#
#   "usemcpc"      : false,
#   "mcpc_build"   : "162",
#
#   "useforge"     : true,
#   "forgeversion" : "152"
#
#   "usemcp"       : true,
#   "mcpversion"   : "mcp62",
# }
# ------------------------------

import os
import sys
import zipfile
import hashlib
import urllib
import errno
import shutil
import json

pythonbin = "python" # "python" should be fine as long as python is in path
root = "/var/lib/jenkins/tools/minecraft" # Where to cache downloaded files
cachedir = os.path.join(root, "cache")

mc_cachedir = os.path.join(cachedir, "minecraft")
mcp_cachedir = os.path.join(cachedir, "mcp")
forge_cachedir = os.path.join(cachedir, "forge")
mcpc_cachedir = os.path.join(cachedir, "mcpc-craftbukkit")


_cwd = os.getcwd()

# Some MCP <-> minecraft version mappings
mcp2mcversion = {
  "mcp50"  : "1.0.0",
  "mcp56"  : "1.1.0",
  "mcp60"  : "1.2.3",
  "mcp61"  : "1.2.4",
  "mcp62"  : "1.2.5",
  "mcp70"  : "1.3.1",
  "mcp70a" : "1.3.1",
  "mcp72"  : "1.3.2",
}

mc2mcpversion = {
  "1.0.0" : "mcp50",
  "1.1.0" : "mcp56",
  "1.2.3" : "mcp60",
  "1.2.4" : "mcp61",
  "1.2.5" : "mcp62",
  "1.3.1" : "mcp70a",
  "1.3.2" : "mcp72",
}



def isint(i):
    try:
        int(i)
        return True
    except:
        return False

def md5sum(fn):
    f = open(fn, "rb")
    f_md5 = hashlib.md5()
    while 1:
        data = f.read(128 * f_md5.block_size)
        if not data:
            break
        f_md5.update(data)
    return f_md5.hexdigest()

def sha1sum(fn):
    f = open(fn, "rb")
    f_sha1 = hashlib.sha1()
    while 1:
        data = f.read(128 * f_sha1.block_size)
        if not data:
            break
        f_sha1.update(data)
    return f_sha1.hexdigest()

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else: raise


def stripstartpath(p, startpath):
    return p.split(startpath, 1)[1][1:]

def unixpathsep(p):
    return p.replace(os.path.sep, "/")

def copydir(src, dst):
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)
    if not os.path.isdir(dst):
        mkdir_p(dst)
    dl = [src]
    startpath = os.path.dirname(src)
    while dl:
        td = dl.pop()
        for f in os.listdir(td):
            f = os.path.join(td, f)
            tf = os.path.join(dst, stripstartpath(f, startpath))
            if os.path.isdir(f):
                sys.stderr.write(f + os.path.sep + " -> " + tf + os.path.sep + "\n")
                print(f + os.path.sep + " -> " + tf + os.path.sep)
                mkdir_p(tf)
                dl.append(f)
            elif os.path.isfile(f):
                sys.stderr.write(f + " -> " + tf + "\n")
                print(f + " -> " + tf)
                shutil.copyfile(f, tf)

def listdir_r(startdir, stripstart = False, useunixpathsep = False):
    startdir = os.path.abspath(startdir)
    _dirs = [startdir]
    files = []
    dirs = []

    while _dirs:
        dir = _dirs.pop(-1)
        for _i in os.listdir(dir):
            item = os.path.join(dir, _i)
            if os.path.isdir(item):
                _dirs.append(item)
                dirs.append(os.path.abspath(item) + os.path.sep)
            elif os.path.isfile(item):
                files.append(os.path.abspath(item))

    x = dirs
    x.extend(files)
    
    if stripstart:
        z = []
        for p in x:
            z.append(stripstartpath(p,startdir))
        x = z
    if useunixpathsep:
        z = []
        for p in x:
            z.append(unixpathsep(p))
        x = z
    x.sort()
    #print x
    return x

def extract(file, path, overwrite=False, verbose=True):
    zip = zipfile.ZipFile(file, "r")
    for item in zip.infolist():
        if item.filename.endswith("/"):
            dirname = os.path.join(path, item.filename)
            mkdir_p(dirname)
            if verbose:
                print "DIR",
                print item.filename
        else:
            filename = os.path.join(path, item.filename)
            dirname = os.path.split(filename)[0]
            mkdir_p(dirname)
            if overwrite or not (not overwrite and os.path.exists(filename)):
                f = open(filename, "w+b")
                data = zip.read(item.filename)
                f.write(data)
                f.close()
                if verbose: print "writing",
            else:
                if verbose: print "skipping",
            if verbose:
                print "FILE",
                print item.filename
    zip.close()

def zipfolders(folderlist, zfn):
        zip1 = zipfile.ZipFile(zfn, "w")
        folderlist.sort()
        for d in folderlist:
            for p in listdir_r(d):
                print p
                zip1.write(p, unixpathsep(stripstartpath(p, d)))
        zip1.close()

def download(url, output=None, overwrite=False):
    if not overwrite and os.path.exists(output):
        return False
    if output:
        return urllib.urlretrieve(url, output)
    else:
        return urllib.urlretrieve(url)

def getZipOrDownload(url, fn, reattempt=1, verbose=True):
    if verbose: print("Attempting to download '%s'." %(url))
    if not os.path.exists(fn):
        if verbose: print("Could not find '%s', downloading from '%s'." %(fn, url))
        download(url, fn)
    try:
        zip = zipfile.ZipFile(fn, "r")
        ret = zip.testzip()
        zip.close()
        if ret != None:
            if reattempt > 0:
                if verbose: print("Zip corrupted, retrying.")
                os.remove(fn)
                return getZipOrDownload(url, fn, reattempt-1)
            else:
                if verbose: print("Zip corrupted.")
                return False
    except:
        if reattempt > 0:
            if verbose: print("Not a zip, retrying.")
            os.remove(fn)
            return getZipOrDownload(url, fn, reattempt-1)
        else:
            if verbose: print("Not a zip.")
            return False
    return fn

def getMinecraftClient(version, verbose=True):
    fn = os.path.join(mc_cachedir, "minecraft_%s.jar" %(version))
    url = "http://assets.minecraft.net/%s/minecraft.jar" %(version.replace(".", "_"))
    return getZipOrDownload(url, fn, verbose)

def getMinecraftServer(version, verbose=True):
    fn = os.path.join(mc_cachedir, "minecraft_server_%s.jar" %(version))
    url = "http://assets.minecraft.net/%s/minecraft_server.jar" %(version.replace(".", "_"))
    return getZipOrDownload(url, fn, verbose)

def getMCP(version, verbose=True):
    fn = os.path.join(mcp_cachedir, "%s.zip" %(version))
    url = "http://mcp.ocean-labs.de/files/%s.zip" %(version)
    return getZipOrDownload(url, fn, verbose)

def getForge(version, verbose=True):
    fvl = getForgeVersionList()
    if fvl.has_key(version):
        fn = os.path.join(forge_cachedir, "minecraftforge-src-%s.zip" %(fvl[version]['version']))
        url = fvl[version]['urls']['src']
        return getZipOrDownload(url, fn, verbose)
    else:
        return False

def getMCPC(version, verbose=True):
    mcpc_versionlist = json.loads(urllib.urlopen("https://api.github.com/repos/MinecraftPortCentral/CraftBukkit/downloads").read())
    for dl in mcpc_versionlist:
        if dl['name'].startswith("craftbukkit-") and dl['name'].endswith(".jar"):
            if dl['name'].split("-")[-1].split(".")[0] == str(version):
                fn = os.path.join(mcpc_cachedir, dl['name'])
                url = dl['html_url']
                return getZipOrDownload(url, fn, verbose)

def getLwjgl(verbose=True):
    fn = os.path.join(cachedir, "lwjgl_minecraft_1.2.5.zip")
    url = "http://mirror.openshell.no/lwjgl_minecraft_1.2.5.zip"
    return getZipOrDownload(url, fn, verbose)

def getMCPVersionList():
    res = {}
    data = urllib.urlopen("http://www.minecraftwiki.net/index.php?title=Minecraft_Coder_Pack&action=raw").read()
    l = data.split("=== History ===")[1].split("|}")[0].split("|-\n")[1:]
    for x in l:
        ld = x.strip("\n|").split("\n|")
        mcpversion = "mcp%s" %(ld[0][1:].replace(".", ""))
        mcclientversion = ld[2]
        mcserverversion = ld[3]
        description = ld[4].replace("<br>", "\n")
        #print("-----")
        #print("MCP Version: %s" %(mcpversion))
        #print("Minecraft client version: %s" %(mcclientversion))
        #print("Minecraft server version: %s" %(mcserverversion))
        #print("Description:")
        #print(description)
        res[mcpversion] = {}
        res[mcpversion]['version'] = mcpversion
        res[mcpversion]['client'] = mcclientversion
        res[mcpversion]['server'] = mcserverversion
        res[mcpversion]['description'] = description
    return res

def getForgeVersionList():
    res = {}
    data = urllib.urlopen("http://files.minecraftforge.net/").read()
    for element in data.split('"'):
        if element.startswith("http") and element.endswith(".zip"):
            fn = element.split("/")[-1]
            spl1 = '.'.join(fn.split(".")[:-1]).split("-")
            _url = element
            _name = spl1[0]
            _type = spl1[1]
            _version = spl1[2]
            if "." in _version:
                _build = _version.split(".")[-1]
            else:
                _build = _version
            if not res.has_key(_build):
                res[_build] = {}
                res[_build]['build'] = _build
                res[_build]['version'] = _version
                res[_build]['urls'] = {}
            res[_build]['urls'][_type] = _url
#    print(res)
    return res

def main():
    sys.stderr.write(str(sys.argv) + "\n")
    print(sys.argv)
    workspace = "."
    if os.environ.has_key("WORKSPACE"):
        workspace = os.environ['WORKSPACE']
    targetdir = os.path.abspath(os.path.join(workspace, "mcp"))

    # Load config file
    config = None
    if len(sys.argv) > 1:
        configfile = os.path.abspath(sys.argv[1])
        if os.path.exists(configfile):
            try: config = json.loads(open(configfile).read())
            except: pass
    if not config:
        configfile = os.path.join(workspace, "mctoolchain.json")
        if os.path.exists(configfile):
            try: config = json.loads(open(configfile).read())
            except: pass
    if not config:
        sys.stderr.write("Could not load the config file.\n")
        exit(6)

    mkdir_p(targetdir)
    mkdir_p(mc_cachedir)
    mkdir_p(mcp_cachedir)
    mkdir_p(mcpc_cachedir)
    mkdir_p(forge_cachedir)


    srcsrc = os.path.join(workspace, "src", "main", "java")
    mc_server_src = os.path.join(srcsrc, "minecraft_server")
    mc_client_src = os.path.join(srcsrc, "minecraft")
    resources = os.path.join(workspace, "src", "main", "resources")
    mc_server_reobf = os.path.join(targetdir, "reobf", "minecraft_server")
    mc_client_reobf = os.path.join(targetdir, "reobf", "minecraft")
    mcmod_info = os.path.join(resources, "mcmod.info")



    mcmod = None
    if os.path.exists(mcmod_info):
        _mcmod = None
        try: _mcmod = json.loads(open(mcmod_info).read())
        except: pass
        if _mcmod:
            for mi in _mcmod:
                if mi['modid'] == config['modid']:
                    mcmod = mi
                    break






#    mcversion = "1.3.2"
    if "clean" in sys.argv or "forceclean" in sys.argv:
        print("Cleaning workspace...")
        print("This is an potentialy destructive action, do you want to continue? (y/N)")
        if not "forceclean" in sys.argv:
            if not raw_input().lower() in ["y", "yes"]:
                print("Aborting...")
                exit(7)
        if os.path.exists(targetdir):
            if os.path.isdir(targetdir):
                print("Removing '%s'..." %(targetdir))
                shutil.rmtree(targetdir)
            else:
                os.remove(targetdir)
        libdir = os.path.join(workspace, "lib")
        if os.path.exists(libdir):
            if os.path.isdir(libdir):
                print("Removing '%s'..." %(libdir))
                shutil.rmtree(libdir)
            else:
                os.remove(libdir)
        outputdir = os.path.join(workspace, "target")
        if os.path.exists(outputdir):
            if os.path.isdir(outputdir):
                print("Removing '%s'..." %(outputdir))
                shutil.rmtree(outputdir)
            else:
                os.remove(outputdir)
        print("Workspace cleaned.")
        

    if "compile" in sys.argv or "package" in sys.argv or "prepare" in sys.argv:
        if config['usemcp']:
            # Prepare MCP, Minecraft client and Minecraft server:
            mcp = getMCP(config['mcpversion'], verbose=True)
            if not mcp:
                sys.stderr.write("[Error] Could not get the MCP zip for version '%s'.\n" %(config['mcpversion']))
                exit(1)
            if mcp2mcversion.has_key(config['mcpversion']):
                mc_client = getMinecraftClient(mcp2mcversion[config['mcpversion']], verbose=True)
                mc_server = getMinecraftServer(mcp2mcversion[config['mcpversion']], verbose=True)
            else:
                mcp_versionlist = getMCPVersionList()
                if mcp_versionlist.has_key(config['mcpversion']):
                    mc_client = getMinecraftClient(mcp_versionlist[config['mcpversion']]["server"], verbose=True)
                    mc_server = getMinecraftServer(mcp_versionlist[config['mcpversion']]["client"], verbose=True)
                    if mc_client and mc_server:
                        pass
                    else:
                        sys.stderr.write("[Error] Could not get Minecraft server '%s' or client '%s' for MCP version '%s'.\n" %(mcp_versionlist[config['mcpversion']]["server"], mcp_versionlist[config['mcpversion']]["client"], config['mcpversion']))
                        exit(3)
                else:
                    sys.stderr.write("[Error] Could not resolve Minecraft version for MCP version '%s'.\n" %(config['mcpversion']))
                    exit(2)
            
            # Prepare LWJGL:
            lwjgl = getLwjgl(verbose=True)
            if not lwjgl:
                sys.stderr.write("[Error] Could not get lwjgl.\n")
                exit(5)
        
            # Prepare Forge:
            if config['useforge']:
                forge = False
                if config['useforge']:
                    forge = getForge(config['forgeversion'], verbose=True)
                    if not forge:
                        sys.stderr.write("[Error] Could not get Forge build '%s'.\n" %(config['forgeversion']))
                        exit(4)
        if config['usemcpc']:
            # Prepare MCPC:
            mcpc = getMCPC(config['mcpc_build'], verbose=True)
    
        if config['usemcp']:
            # Install MCP to workspace:
            print(mcp)
            extract(mcp, targetdir)
            mkdir_p(os.path.join(targetdir, "jars", "bin"))
        
            # Install Minecraft client to workspace:
            print(mc_client)
            shutil.copy(mc_client, os.path.join(targetdir, "jars", "bin", "minecraft.jar"))
        
            # Install LWJGL to workspace:
            print(lwjgl)
            extract(lwjgl, os.path.join(targetdir, "jars", "bin"))
        
            # Install Minecraft server to workspace:
            print(mc_server)
            shutil.copy(mc_server, os.path.join(targetdir, "jars", "minecraft_server.jar"))
    
            if config['useforge']:
                # Install Forge to workspace
                print(forge)
                extract(forge, targetdir)
                os.chdir(os.path.join(targetdir, "forge"))
                os.system("%s install.py" %(pythonbin))
        if config['usemcpc']:
            # Install MCPC
            mkdir_p(os.path.join(workspace, "lib"))
            shutil.copy(mcpc, os.path.join(workspace, "lib", "mcpc-craftbukkit.jar"))
            if config['usemcp']:
                mkdir_p(os.path.join(targetdir, "lib"))
                shutil.copy(mcpc, os.path.join(targetdir, "lib", "mcpc-craftbukkit.jar"))

    # Compile...
    if "compile" in sys.argv or "package" in sys.argv:
        if config['usemcp']:
            if os.path.exists(mc_client_src):
                copydir(mc_client_src, os.path.join(targetdir, "src" + os.path.sep))
            if os.path.exists(mc_server_src):
                copydir(mc_server_src, os.path.join(targetdir, "src" + os.path.sep))
            os.chdir(os.path.join(targetdir))
            os.system("%s %s" %(pythonbin, os.path.join("runtime", "recompile.py")))
            os.system("%s %s" %(pythonbin, os.path.join("runtime", "reobfuscate.py")))
            
            outputdir = os.path.join(workspace, "target")
            mkdir_p(outputdir)
            
            mkdir_p(resources)
            

            
            mf = open(os.path.join(resources, "mcp-jenkins-buildinfo.txt"), "wb")
            if os.environ.has_key("JENKINS_URL"):
                mf.write("Jenkins URL: " + os.environ['JENKINS_URL'] + "\r\n")
            if os.environ.has_key("JOB_URL"):
                mf.write("Job URL: " + os.environ['JOB_URL'] + "\r\n")
            if os.environ.has_key("BUILD_URL"):
                mf.write("Build URL: " + os.environ['BUILD_URL'] + "\r\n")
            if os.environ.has_key("JOB_NAME"):
                mf.write("Job name: " + os.environ['JOB_NAME'] + "\r\n")
            if os.environ.has_key("BUILD_ID"):
                mf.write("Build id: " + os.environ['BUILD_ID'] + "\r\n")
            if os.environ.has_key("BUILD_NUMBER"):
                mf.write("Build number: " + os.environ['BUILD_NUMBER'] + "\r\n")
            if os.environ.has_key("NODE_NAME"):
                mf.write("Node name: " + os.environ['NODE_NAME'] + "\r\n")
            if os.environ.has_key("NODE_LABELS"):
                mf.write("Node labels: " + os.environ['NODE_LABELS'] + "\r\n")
            mf.close()

            prefix=""
            suffix=""

#    "modid": "mod_UrbanCraftCoins",
#    "name": "UrbanCraft Coins",
#    "version": "0.01",
#    "mcversion": "1.2.5",

            if mcmod:
                prefix = prefix + mcmod['modid'] + "-"
                suffix = suffix + "-" + mcmod['version']
                suffix = suffix + "-mc" + mcmod['mcversion']
            if os.environ.has_key("JOB_NAME"):
                if not mcmod:
                    prefix = prefix + unixpathsep(os.environ['JOB_NAME']).replace("/", "_") + "-"
            if os.environ.has_key("GIT_COMMIT"):
                suffix = suffix + "-" + os.environ['GIT_COMMIT'][0:10]
            if os.environ.has_key("BUILD_NUMBER"):
                suffix = suffix + "-jnks_" + os.environ['BUILD_NUMBER']

            if os.path.exists(mc_client_reobf):
                zipfolders([mc_client_reobf, resources], os.path.join(outputdir, prefix + "Client" + suffix + ".jar"))
            if os.path.exists(mc_server_reobf):
                zipfolders([mc_server_reobf, resources], os.path.join(outputdir, prefix + "Server" + suffix + ".jar"))
            
            

        else:
            print("Nothing to compile.")

if __name__ == "__main__":
    main()
