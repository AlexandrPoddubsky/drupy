#!/usr/bin/env python

# $Id: bootstrap.inc,v 1.211 2008/05/26 17:12:54 dries Exp $

"""
@package Drupy
@see http://drupy.net
@note Drupy is a port of the Drupal project.
 The drupal project can be found at http://drupal.org
@file bootstrap.py (ported from Drupal's bootstrap.inc)
 Functions that need to be loaded on every Drupal request.
@author Brendon Crawford
@copyright 2008 Brendon Crawford
@contact message144 at users dot sourceforge dot net
@created 2008-01-10
@version 0.1
@license: 

 This program is free software; you can redistribute it and/or
 modify it under the terms of the GNU General Public License
 as published by the Free Software Foundation; either version 2
 of the License, or (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

#
# INcludes
#
from lib.drupy import DrupyPHP as p
from sites.default import settings
import cache as inc_cache
import database as inc_database
import session as inc_session
import theme_maintenance as inc_theme_maintenance
import module as inc_module
import path as inc_path
import common as inc_common
import language as inc_language


#
# Global variables
#
user = None
base_path_ = None
base_root = None
base_url = None
language_ = None
timers = None



#
# Indicates that the item should never be removed unless explicitly told to
# using cache_clear_all() with a cache ID.
#
CACHE_PERMANENT = 0

#
# Indicates that the item should be removed at the next general cache wipe.
#
CACHE_TEMPORARY = -1

#
# Indicates that page caching is disabled.
#
CACHE_DISABLED = 0

#
# Indicates that page caching is enabled, using "normal" mode.
#
CACHE_NORMAL = 1

#
# Indicates that page caching is using "aggressive" mode. This bypasses
# loading any modules for additional speed, which may break functionality in
# modules that expect to be run on each page load.
#
CACHE_AGGRESSIVE = 2

#
# Log message severity -- Alert: action must be taken immediately.
#
# @see watchdog()
# @see watchdog_severity_levels()
#

WATCHDOG_ALERT = 1

#
# Log message severity -- Critical: critical conditions.
#
# @see watchdog()
# @see watchdog_severity_levels()
#
WATCHDOG_CRITICAL = 2

#
# Log message severity -- Error: error conditions.
#
# @see watchdog()
# @see watchdog_severity_levels()
#

WATCHDOG_ERROR = 3

#
# Log message severity -- Warning: warning conditions.
#
# @see watchdog()
# @see watchdog_severity_levels()
#

WATCHDOG_WARNING = 4

#
# Log message severity -- Notice: normal but significant condition.
#
# @see watchdog()
# @see watchdog_severity_levels()
#
WATCHDOG_NOTICE = 5

#
# Log message severity -- Informational: informational messages.
#
# @see watchdog()
# @see watchdog_severity_levels()
#

WATCHDOG_INFO = 6

#
# Log message severity -- Debug: debug-level messages.
#
# @see watchdog()
# @see watchdog_severity_levels()
#

WATCHDOG_DEBUG = 7

#
# First bootstrap phase: initialize configuration.
#
DRUPAL_BOOTSTRAP_CONFIGURATION = 0

#
# Second bootstrap phase: try to call a non-database cache
# fetch routine.
#
DRUPAL_BOOTSTRAP_EARLY_PAGE_CACHE = 1

#
# Third bootstrap phase: initialize database layer.
#
DRUPAL_BOOTSTRAP_DATABASE = 2

#
# Fourth bootstrap phase: identify and reject banned hosts.
#
DRUPAL_BOOTSTRAP_ACCESS = 3

#
# Fifth bootstrap phase: initialize session handling.
#
DRUPAL_BOOTSTRAP_SESSION = 4

#
# Sixth bootstrap phase: load bootstrap.inc and module.inc, start
# the variable system and try to serve a page from the cache.
#
DRUPAL_BOOTSTRAP_LATE_PAGE_CACHE = 5

#
# Seventh bootstrap phase: find out language of the page.
#
DRUPAL_BOOTSTRAP_LANGUAGE = 6

#
# Eighth bootstrap phase: set p.GET['q'] to Drupal path of request.
#
DRUPAL_BOOTSTRAP_PATH = 7

#
# Final bootstrap phase: Drupal is fully loaded; validate and fix
# input data.
#
DRUPAL_BOOTSTRAP_FULL = 8

#
# Role ID for anonymous users; should match what's in the "role" table.
#
DRUPAL_ANONYMOUS_RID = 9

#
# Role ID for authenticated users; should match what's in the "role" table.
#
DRUPAL_AUTHENTICATED_RID = 10

#
# No language negotiation. The default language is used.
#
LANGUAGE_NEGOTIATION_NONE = 0

#
# Path based negotiation with fallback to default language
# if no defined path prefix identified.
#
LANGUAGE_NEGOTIATION_PATH_DEFAULT = 1

#
# Path based negotiation with fallback to user preferences
# and browser language detection if no defined path prefix
# identified.
#
LANGUAGE_NEGOTIATION_PATH = 2

#
# Domain based negotiation with fallback to default language
# if no language identified by domain.
#
LANGUAGE_NEGOTIATION_DOMAIN = 3


def timer_start(name):
  """
   Start the timer with the specified name. If you start and stop
   the same timer multiple times, the measured intervals will be
   accumulated.
  
   @param name
     The name of the timer.
  """
  global timers;
  if timers == None:
    timers = {};
  if not p.isset(timers, name):
    timers[name] = {}
  (usec, sec) = p.explode(' ', p.microtime());
  timers[name]['start'] = float(usec) + float(sec);
  timers[name]['count'] = ((timers[name]['count'] + 1) if p.isset(timers[name],'count') else 1);


def timer_read(name):
  """
   Read the current timer value without stopping the timer.
  
   @param name
     The name of the timer.
   @return
     The current timer value in ms.
  """
  global timers;
  if (p.isset(timers[name], 'start')):
    (usec, sec) = p.explode(' ', p.microtime());
    stop = float(usec) + float(sec);
    diff = round((stop - timers[name]['start']) * 1000, 2);
    if (p.isset(timers[name], 'time')):
      diff += timers[name]['time'];
    return diff;


def timer_stop(name):
  """
   Stop the timer with the specified name.
  
   @param name
     The name of the timer.
   @return
     A timer array. The array contains the number of times the
     timer has been started and stopped (count) and the accumulated
     timer value in ms (time).
  """
  global timers;
  timers[name]['time'] = timer_read(name);
  del(timers[name]['start']);
  return timers[name];


def conf_path(require_settings = True, reset = False):
  """
   Find the appropriate configuration directory.
  
   Try finding a matching configuration directory by stripping the website's
   hostname from left to right and pathname from right to left. The first
   configuration file found will be used; the remaining will ignored. If no
   configuration file is found, return a default value 'confdir/default'.
  
   Example for a fictitious site installed at
   http://www.drupal.org:8080/mysite/test/ the 'settings.php' is searched in
   the following directories:
  
    1. confdir/8080.www.drupal.org.mysite.test
    2. confdir/www.drupal.org.mysite.test
    3. confdir/drupal.org.mysite.test
    4. confdir/org.mysite.test
  
    5. confdir/8080.www.drupal.org.mysite
    6. confdir/www.drupal.org.mysite
    7. confdir/drupal.org.mysite
    8. confdir/org.mysite
  
    9. confdir/8080.www.drupal.org
   10. confdir/www.drupal.org
   11. confdir/drupal.org
   12. confdir/org
  
   13. confdir/default
  
   @param require_settings
     Only configuration directories with an existing settings.php file
     will be recognized. Defaults to TRUE. During initial installation,
     this is set to FALSE so that Drupal can detect a matching directory,
     then create a new settings.php file in it.
   @param reset
     Force a full search for matching directories even if one had been
     found previously.
   @return
     The path of the matching directory.
  """
  pass


def drupal_unset_globals():
  """
   Unsets all disallowed global variables. See allowed for what's allowed.
  """
  # Do nothing
  pass;


def conf_init():
  """
   Loads the configuration and sets the base URL, cookie domain, and
   session name correctly.
  """
  global base_path_, base_root, base_url;
  # These will come from settings
  # db_url, db_prefix, cookie_domain, conf, installed_profile, update_free_access
  if (base_url != None):
    # Parse fixed base URL from settings.php.
    parts = p.parse_url(base_url);
    if (not p.isset(parts, 'path')):
      parts['path'] = '';
    base_path_ = parts['path'] + '/';
    # Build base_root (everything until first slash after "scheme://").
    base_root = p.substr(base_url, 0, p.strlen(base_url) - p.strlen(parts['path']));
  else:
    # Create base URL
    base_root = ('https' if (p.isset(p.SERVER, 'HTTPS') and p.SERVER['HTTPS'] == 'on') else 'http');
    # As p.SERVER['HTTP_HOST'] is user input, ensure it only contains
    # characters allowed in hostnames.
    base_root += '://' + p.preg_replace('/[^a-z0-9-:._]/i', '', p.SERVER['HTTP_HOST']);
    base_url = base_root;
    # p.SERVER['SCRIPT_NAME'] can, in contrast to p.SERVER['PHP_SELF'], not
    # be modified by a visitor.
    dir = p.trim(p.dirname(p.SERVER['SCRIPT_NAME']), '\,/');
    if (len(dir) > 0):
      base_path_ = "/dir";
      base_url += base_path_;
      base_path_ += '/';
    else:
      base_path_ = '/';
  if (settings.cookie_domain != None):
    # If the user specifies the cookie domain, also use it for session name.
    session_name_ = settings.cookie_domain;
  else:
    # Otherwise use base_url as session name, without the protocol
    # to use the same session identifiers across http and https.
    (dummy_, session_name_) = p.explode('://', base_url, 2);
    # We escape the hostname because it can be modified by a visitor.
    if (not p.empty(p.SERVER['HTTP_HOST'])):
      settings.cookie_domain = check_plain(p.SERVER['HTTP_HOST']);
  # Strip leading periods, www., and port numbers from cookie domain.
  settings.cookie_domain = p.ltrim(settings.cookie_domain, '.');
  if (p.strpos(settings.cookie_domain, 'www.') == 0):
    settings.cookie_domain = p.substr(settings.cookie_domain, 4);
  settings.cookie_domain = p.explode(':', settings.cookie_domain);
  settings.cookie_domain = '.' + settings.cookie_domain[0];
  # Per RFC 2109, cookie domains must contain at least one dot other than the
  # first. For hosts such as 'localhost' or IP Addresses we don't set a cookie domain.
  if (p.count(p.explode('.', settings.cookie_domain)) > 2 and not p.is_numeric(p.str_replace('.', '', settings.cookie_domain))):
    p.ini_set('session.cookie_domain', settings.cookie_domain);
  #print session_name;
  inc_session.sess_name('SESS' + p.md5(session_name_));



def drupal_get_filename(type_, name, filename = None):
  """
   Returns and optionally sets the filename for a system item (module,
   theme, etc.). The filename, whether provided, cached, or retrieved
   from the database, is only returned if the file exists.
  
   This def plays a key role in allowing Drupal's resources (modules
   and themes) to be located in different places depending on a site's
   configuration. For example, a module 'foo' may legally be be located
   in any of these three places:
  
   modules/foo/foo.module
   sites/all/modules/foo/foo.module
   sites/example.com/modules/foo/foo.module
  
   Calling drupal_get_filename('module', 'foo') will give you one of
   the above, depending on where the module is located.
  
   @param type
     The type of the item (i.e. theme, theme_engine, module).
   @param name
     The name of the item for which the filename is requested.
   @param filename
     The filename of the item if it is to be set explicitly rather
     than by consulting the database.
  
   @return
     The filename of the requested item.
  """
  p.static(drupal_get_filename, 'files', {})
  file = inc_database.db_result(inc_database.db_query("SELECT filename FROM {system} WHERE name = '%s' AND type = '%s'", name, type_))
  if (not p.isset(drupal_get_filename.files, type_)):
    drupal_get_filename.files[type_] = {}
  if (filename != None and p.file_exists(filename)):
    drupal_get_filename.files[type_][name] = filename;
  elif (p.isset(drupal_get_filename.files[type_], name)):
    # nothing
    pass;
  # Verify that we have an active database connection, before querying
  # the database.  This is required because this def is called both
  # before we have a database connection (i.e. during installation) and
  # when a database connection fails.
  elif (db_is_active() and (file and p.file_exists(file))):
    drupal_get_filename.files[type_][name] = file;
  else:
    # Fallback to searching the filesystem if the database connection is
    # not established or the requested file is not found.
    config = conf_path();
    dir_ = ('themes/engines' if (type_ == 'theme_engine') else (type_ + 's'));
    file = (("%(name)s.engine" % {'name':name}) if (type_ == 'theme_engine') else ("%(name)s.type" % {'name':name}));
    fileVals = {'name':name, 'file':file, 'dir':dir_, 'config':config};
    fileChecker = [
      "config/dir/file" % fileVals,
      "config/dir/name/file" % fileVals,
      "dir/file" % fileVals,
      "dir/name/file" % fileVals
    ];
    for file_ in fileChecker:
      if (p.file_exists(file_)):
        drupal_get_filename.files[type_][name] = file_;
        break;
  if (p.isset(drupal_get_filename.files[type_], name)):
    return drupal_get_filename.files[type_][name];



def variable_init(conf_ = {}):
  """
   Load the persistent variable table.
  
   The variable table is composed of values that have been saved in the table
   with variable_set() as well as those explicitly specified in the configuration
   file.
  """  
  # NOTE: caching the variables improves performance by 20% when serving cached pages.
  cached = inc_cache.cache_get('variables', 'cache');
  if (cached):
    variables = cached.data;
  else:
    variables = {}
    result = inc_database.db_query('SELECT * FROM {variable}');
    while True:
      variable = inc_database.db_fetch_object(result);
      if (not variable):
        break;
      variables[variable.name] = p.unserialize(variable.value);
    inc_cache.cache_set('variables', variables);
  for name,value in conf_.items():
    variables[name] = value;
  return variables;



def variable_get(name, default_):
  """
   Return a persistent variable.
  
   @param name
     The name of the variable to return.
   @param default
     The default value to use if this variable has never been set.
   @return
     The value of the variable.
  """
  return  (settings.conf[name] if p.isset(settings.conf, name) else default_);


def variable_set(name, value):
  """
   Set a persistent variable.
  
   @param name
     The name of the variable to set.
   @param value
     The value to set. This can be any PHP data type; these functions take care
     of serialization as necessary.
  """
  serialized_value = p.serialize(value);
  db_query("UPDATE {variable} SET value = '%s' WHERE name = '%s'", serialized_value, name);
  if (db_affected_rows() == 0):
    db_query("INSERT INTO {variable} (name, value) VALUES ('%s', '%s')", name, serialized_value);
  cache_clear_all('variables', 'cache');
  settings.conf[name] = value;


def variable_del(name):
  """
   Unset a persistent variable.
  
   @param name
     The name of the variable to undefine.
  """
  db_query("DELETE FROM {variable} WHERE name = '%s'", name);
  cache_clear_all('variables', 'cache');
  del(settings.conf[name]);



def page_get_cache():
  """
   Retrieve the current page from the cache.
  
   Note: we do not serve cached pages when status messages are waiting (from
   a redirected form submission which was completed).
  
   @param status_only
     When set to TRUE, retrieve the status of the page cache only
     (whether it was started in this request or not).
  """
  cache = None;
  if (user == None and p.SERVER['p.REQUEST_METHOD'] == 'p.GET' and p.count(drupal_set_message()) == 0):
    cache = cache_get(base_root + request_uri(), 'cache_page');
    if (p.empty(cache)):
      ob_start()
  return cache;



def bootstrap_invoke_all(hook):
  """
   Call all init or exit hooks without including all modules.
  
   @param hook
     The name of the bootstrap hook we wish to invoke.
  """
  for module_ in inc_module.module_list(True, True):
    inc_module.module_invoke(module_, hook);


def drupal_load(type_, name):
  """
   Includes a file with the provided type and name. This prevents
   including a theme, engine, module, etc., more than once.
  
   @param type
     The type of item to load (i.e. theme, theme_engine, module).
   @param name
     The name of the item to load.
  
   @return
     TRUE if the item is loaded or has already been loaded.
  """
  p.static(drupal_load, 'files', {})
  if (not p.isset(drupal_load.files, type)):
    drupal_load.files[type_] = {}
  if (p.isset(drupal_load.files[type_], name)):
    return True
  else:
    filename = drupal_get_filename(type_, name);
    if (filename != False):
      p.include_once("./" + filename);
      drupal_load.files[type_][name] = True;
      return True;
    else:
      return False;


def drupal_page_header():
  """
   Set HTTP headers in preparation for a page response.
  
   Authenticated users are always given a 'no-cache' p.header, and will
   fetch a fresh page on every request.  This prevents authenticated
   users seeing locally cached pages that show them as logged out.
  
   @see page_set_cache()
  """
  p.header("Expires: Sun, 19 Nov 1978 05:00:00 GMT");
  p.header("Last-Modified: " + p.gmdate("%D, %d %M %Y %H:%i:%s") + " GMT");
  p.header("Cache-Control: store, no-cache, must-revalidate");
  p.header("Cache-Control: post-check=0, pre-check=0", False);



def drupal_page_cache_header(cache):
  """
   Set HTTP headers in preparation for a cached page response.
  
   The general approach here is that anonymous users can keep a local
   cache of the page, but must revalidate it on every request.  Then,
   they are given a '304 Not Modified' response as long as they stay
   logged out and the page has not been modified.
  """
  # Set default values:
  last_modified = p.gmdate('D, d M Y H:i:s', cache.created) + ' GMT';
  etag = '"' + drupy_md5(last_modified) + '"';
  # See if the client has provided the required HTTP headers:
  if_modified_since =  (p.stripslashes(p.SERVER['HTTP_IF_MODIFIED_SINCE']) \
    if p.isset(p.SERVER, 'HTTP_IF_MODIFIED_SINCE') else False);
  if_none_match = (p.stripslashes(p.SERVER['HTTP_IF_NONE_MATCH']) \
    if p.isset(p.SERVER, 'HTTP_IF_NONE_MATCH') else False);
  if (if_modified_since and if_none_match
      and if_none_match == etag # etag must match
      and if_modified_since == last_modified):  # if-modified-since must match
    p.header('HTTP/1.1 304 Not Modified');
    # All 304 responses must send an etag if the 200 response for the same object contained an etag
    p.header("Etag: %(etag)s" % {'etag':etag});
    exit();
  # Send appropriate response:
  p.header("Last-Modified: %(last_modified)s" % {'last_modified':last_modified});
  p.header("Etag: %(etag)s" % {'etag':etag});
  # The following headers force validation of cache:
  p.header("Expires: Sun, 19 Nov 1978 05:00:00 GMT");
  p.header("Cache-Control: must-revalidate");
  if (variable_get('page_compression', True)):
    # Determine if the browser accepts gzipped data.
    if (p.strpos(p.SERVER['HTTP_ACCEPT_ENCODING'], 'gzip') == False and p.function_exists('gzencode')):
      # Strip the gzip p.header and run uncompress.
      cache.data = p.gzinflate(p.substr(p.substr(cache.data, 10), 0, -8));
    elif (p.function_exists('gzencode')):
      p.header('Content-Encoding: gzip');
  # Send the original request's headers. We send them one after
  # another so PHP's p.header() def can deal with duplicate
  # headers.
  headers = p.explode("\n", cache.headers);
  for p.header_ in headers:
    p.header(p.header_);
  print cache.data;


def bootstrap_hooks():
  """
   Define the critical hooks that force modules to always be loaded.
  """
  return ['boot', 'exit'];


def drupal_unpack(obj, field = 'data'):
  """
   Unserializes and appends elements from a serialized string.
  
   @param obj
     The object to which the elements are appended.
   @param field
     The attribute of obj whose value should be unserialized.
  """
  data = p.unserialize(obj.field);
  if (obj.field and not p.empty(data)):
    for key,value in data.items():
      if (not p.isset(obj, key)):
        setattr(obj, key, value);
  return obj;


def referer_uri():
  """
   Return the URI of the referring page.
  """
  if (p.isset(p.SERVER, 'HTTP_REFERER')):
    return p.SERVER['HTTP_REFERER'];


def check_plain(text):
  """
   Encode special characters in a plain-text string for display as HTML.
  
   Uses drupal_validate_utf8 to prevent cross site scripting attacks on
   Internet Explorer 6.
  """
  return (p.htmlspecialchars(text, p.ENT_QUOTES) if drupal_validate_utf8(text) else '');


def drupal_validate_utf8(text):
  """
   Checks whether a string is valid UTF-8.
  
   All functions designed to filter input should use drupal_validate_utf8
   to ensure they operate on valid UTF-8 strings to prevent bypass of the
   filter.
  
   When text containing an invalid UTF-8 lead byte (0xC0 - 0xFF) is presented
   as UTF-8 to Internet Explorer 6, the program may misinterpret subsequent
   bytes. When these subsequent bytes are HTML control characters such as
   quotes or angle brackets, parts of the text that were deemed safe by filters
   end up in locations that are potentially unsafe; An onerror attribute that
   is outside of a tag, and thus deemed safe by a filter, can be interpreted
   by the browser as if it were inside the tag.
  
   This def exploits preg_match behaviour (since PHP 4.3.5) when used
   with the u modifier, as a fast way to find invalid UTF-8. When the matched
   string contains an invalid byte sequence, it will fail silently.
  
   preg_match may not fail on 4 and 5 octet sequences, even though they
   are not supported by the specification.
  
   The specific preg_match behaviour is present since PHP 4.3.5.
  
   @param text
     The text to check.
   @return
     TRUE if the text is valid UTF-8, FALSE if not.
  """
  if (p.strlen(text) == 0):
    return True;
  return (p.preg_match('/^./us', text) == 1);


def request_uri():
  """
   Since p.SERVER['p.REQUEST_URI'] is only available on Apache, we
   generate an equivalent using other environment variables.
  """
  if (p.isset(p.SERVER, 'REQUEST_URI')):
    uri = p.SERVER['REQUEST_URI'];
  else:
    if (p.isset(p.SERVER, 'argv')):
      uri = p.SERVER['SCRIPT_NAME'] + '?' + p.SERVER['argv'][0];
    elif (p.isset(p.SERVER, 'QUERY_STRING')):
      uri = p.SERVER['SCRIPT_NAME'] + '?' + p.SERVER['QUERY_STRING'];
    else:
      uri = p.SERVER['SCRIPT_NAME'];
  return uri;



def watchdog(type, message, variables = [], severity = WATCHDOG_NOTICE, link = None):
  """
   Log a system message.
  
   @param type
     The category to which this message belongs.
   @param message
     The message to store in the log. See t() for documentation
     on how message and variables interact. Keep message
     translatable by not concatenating dynamic values into it!
   @param variables
     Array of variables to replace in the message on display or
     NULL if message is already translated or not possible to
     translate.
   @param severity
     The severity of the message, as per RFC 3164
   @param link
     A link to associate with the message.
  
   @see watchdog_severity_levels()
  """
  # Prepare the fields to be logged
  log_message = {
    'type'        : type,
    'message'     : message,
    'variables'   : variables,
    'severity'    : severity,
    'link'        : link,
    'user'        : user,
    'request_uri' : base_root + request_uri(),
    'referer'     : referer_uri(),
    'ip'          : ip_address(),
    'timestamp'   : p.time_(),
  }
  # Call the logging hooks to log/process the message
  for module in inc_module.module_implements('watchdog', True):
    module_invoke(module, 'watchdog', log_message);


def drupal_set_message(message = None, type = 'status', repeat = True):
  """
   Set a message which reflects the status of the performed operation.
  
   If the def is called with no arguments, this def returns all set
   messages without clearing them.
  
   @param message
     The message should begin with a capital letter and always ends with a
     period '.'.
   @param type
     The type of the message. One of the following values are possible:
     - 'status'
     - 'warning'
     - 'error'
   @param repeat
     If this is FALSE and the message is already set, then the message won't
     be repeated.
  """
  if (message):
    if (not p.isset(p.SESSION, 'messages')):
      p.SESSION['messages'] = {};
    if (not p.isset(p.SESSION['messages'], type)):
      p.SESSION['messages'][type] = [];
    if (repeat or not p.in_array(message, p.SESSION['messages'][type])):
      p.SESSION['messages'][type].append( message );
  # messages not set when DB connection fails
  return  (p.SESSION['messages'] if p.isset(p.SESSION, 'messages') else None);


def drupal_get_messages(type = None, clear_queue = True):
  """
   Return all messages that have been set.
  
   @param type
     (optional) Only return messages of this type.
   @param clear_queue
     (optional) Set to FALSE if you do not want to clear the messages queue
   @return
     An associative array, the key is the message type, the value an array
     of messages. If the type parameter is passed, you get only that type,
     or an empty array if there are no such messages. If type is not passed,
     all message types are returned, or an empty array if none exist.
  """
  messages = drupal_set_message();
  if (not p.empty('messages')):
    if (type != None and type != False):
      if (clear_queue):
        del(p.SESSION['messages'][type]);
      if (p.isset(messages, type)):
        return {type : messages[type]};
    else:
      if (clear_queue):
        del(p.SESSION['messages']);
      return messages;
  return {};


def drupal_is_denied(ip):
  """
   Check to see if an IP address has been blocked.
  
   Blocked IP addresses are stored in the database by default. However for
   performance reasons we allow an override in settings.php. This allows us
   to avoid querying the database at this critical stage of the bootstrap if
   an administrative interface for IP address blocking is not required.
  
   @param $ip string
     IP address to check.
   @return bool
     TRUE if access is denied, FALSE if access is allowed.
  """
  # Because this function is called on every page request, we first check
  # for an array of IP addresses in settings.php before querying the
  # database.
  blocked_ips = variable_get('blocked_ips', None);
  if (blocked_ips != None and p.is_array(blocked_ips)):
    return p.in_array(ip, blocked_ips)
  else:
    sql = "SELECT 1 FROM {blocked_ips} WHERE ip = '%s'";
    return (inc_database.db_result(inc_database.db_query(sql, ip)) != False)


def drupal_anonymous_user(session = ''):
  """
   Generates a default anonymous user object.
  
   @return Object - the user object.
  """
  user = p.stdClass();
  user.uid = 0;
  user.hostname = ip_address();
  user.roles = {};
  user.roles[DRUPAL_ANONYMOUS_RID] = 'anonymous user';
  user.session = session;
  user.cache = 0;
  return user;



def drupal_bootstrap(phase):
  """
   A string describing a phase of Drupal to load. Each phase adds to the
   previous one, so invoking a later phase automatically runs the earlier
   phases too. The most important usage is that if you want to access the
   Drupal database from a script without loading anything else, you can
   include bootstrap.inc, and call drupal_bootstrap(DRUPAL_BOOTSTRAP_DATABASE).
  
   @param phase
     A constant. Allowed values are:
       DRUPAL_BOOTSTRAP_CONFIGURATION: initialize configuration.
       DRUPAL_BOOTSTRAP_EARLY_PAGE_CACHE: try to call a non-database cache fetch routine.
       DRUPAL_BOOTSTRAP_DATABASE: initialize database layer.
       DRUPAL_BOOTSTRAP_ACCESS: identify and reject banned hosts.
       DRUPAL_BOOTSTRAP_SESSION: initialize session handling.
       DRUPAL_BOOTSTRAP_LATE_PAGE_CACHE: load bootstrap.inc and module.inc, start
         the variable system and try to serve a page from the cache.
       DRUPAL_BOOTSTRAP_LANGUAGE: identify the language used on the page.
       DRUPAL_BOOTSTRAP_PATH: set p.GET['q'] to Drupal path of request.
       DRUPAL_BOOTSTRAP_FULL: Drupal is fully loaded, validate and fix input data.
  """
  # DRUPY(BC): Why were these set as static vars?
  # No longer needed. 
  phase_index = 0;
  phases = range(DRUPAL_BOOTSTRAP_CONFIGURATION, DRUPAL_BOOTSTRAP_FULL+1);
  while (phase >= phase_index and p.isset(phases, phase_index)):
    current_phase = phases[phase_index];
    #Drupal was unsetting the phase var here.
    #This was completely unnecessary and most likely the cause of some bugs
    phase_index += 1;
    _drupal_bootstrap(current_phase);



def _drupal_bootstrap(phase):
  global conf
  if phase == DRUPAL_BOOTSTRAP_CONFIGURATION:
    # Start a page timer:
    timer_start('page');
    # Initialize the configuration
    conf_init();
  elif phase == DRUPAL_BOOTSTRAP_EARLY_PAGE_CACHE:
    # Allow specifying special cache handlers in settings.php, like
    # using memcached or files for storing cache information.
    # If the page_cache_fastpath is set to TRUE in settings.php and
    # page_cache_fastpath (implemented in the special implementation of
    # cache.inc) printed the page and indicated this with a returned TRUE
    # then we are done.
    if (variable_get('page_cache_fastpath', False) and page_cache_fastpath()):
      exit();
  elif phase == DRUPAL_BOOTSTRAP_DATABASE:
    # Initialize the default database.
    inc_database.db_set_active();
    # Register autoload functions so that we can access classes and interfaces.
    # spl_autoload_register('drupal_autoload_class')
    # spl_autoload_register('drupal_autoload_interface')
  elif phase == DRUPAL_BOOTSTRAP_ACCESS:
    # Deny access to blocked IP addresses - t() is not yet available
    if (drupal_is_denied(ip_address())):
      p.header('HTTP/1.1 403 Forbidden');
      print 'Sorry, ' + check_plain(ip_address()) + ' has been banned.';
      exit()
  elif phase == DRUPAL_BOOTSTRAP_SESSION:
    p.session_set_save_handler('sess_open', 'sess_close', 'sess_read', 'sess_write', 'sess_destroy_sid', 'sess_gc');
    p.session_start();
  elif phase == DRUPAL_BOOTSTRAP_LATE_PAGE_CACHE:
    # Initialize configuration variables, using values from settings.php if available.
    settings.conf = variable_init( ({} if (settings.conf == None) else settings.conf) );
    # Load module handling.
    cache_mode = variable_get('cache', CACHE_DISABLED);
    # Get the page from the cache.
    cache =  ('' if (cache_mode == CACHE_DISABLED) else page_get_cache());
    # If the skipping of the bootstrap hooks is not enforced, call hook_boot.
    if (cache_mode != CACHE_AGGRESSIVE):
      bootstrap_invoke_all('boot');
    # If there is a cached page, display it.
    if (cache):
      drupal_page_cache_header(cache);
      # If the skipping of the bootstrap hooks is not enforced, call hook_exit.
      if (cache_mode != CACHE_AGGRESSIVE):
        bootstrap_invoke_all('exit');
      # We are done.
      exit();
    # Prepare for non-cached page workflow.
    drupal_page_header();
  elif phase == DRUPAL_BOOTSTRAP_LANGUAGE:
    drupal_init_language();
  elif phase == DRUPAL_BOOTSTRAP_PATH:
    # Initialize p.GET['q'] prior to loading modules and invoking hook_init().
    #inc_path.drupal_init_path();
    pass
  elif phase == DRUPAL_BOOTSTRAP_FULL:
    inc_common._drupal_bootstrap_full();


def drupal_maintenance_theme():
  """
   Enables use of the theme system without requiring database access.
  
   Loads and initializes the theme system for site installs, updates and when
   the site is in off-line mode. This also applies when the database fails.
  
   @see _drupal_maintenance_theme()
  """
  inc_theme_maintenance._drupal_maintenance_theme();


def get_t():
  """
   Return the name of the localisation function. Use in code that needs to
   run both during installation and normal operation.
  """
  p.static(get_t, 't')
  if (get_t.t == None):
    get_t.t =  ('st' if p.function_exists('install_main') else 't');
  return get_t.t;



def drupal_init_language():
  """
    Choose a language for the current page, based on site and user preferences.
  """
  global language_
  # Ensure the language is correctly returned, even without multilanguage support.
  # Useful for eg. XML/HTML 'lang' attributes.
  if (variable_get('language_count', 1) == 1):
    language_ = language_default();
  else:
    language_ = inc_language.language_initialize();


def language_list(field = 'language', reset = False):
  """
   Get a list of languages set up indexed by the specified key
  
   @param field The field to index the list with.
   @param reset Boolean to request a reset of the list.
  """
  p.static(language_list, 'languages')
  # Reset language list
  if (reset):
    languages_list.languages = {};
  # Init language list
  if (languages_list.languages == None):
    if (variable_get('language_count', 1) > 1 or module_exists('locale')):
      result = db_query('SELECT# FROM {languages} ORDER BY weight ASC, name ASC');
      while True:
        row = db_fetch_object(result);
        if row == None:
          break;
        languages_list.languages['language'][row.language] = row;
    else:
      # No locale module, so use the default language only.
      default_ = language_default();
      languages_list.languages['language'][default_.language] = default_;
  # Return the array indexed by the right field
  if (not p.isset(languages_list.languages, field)):
    languages_list.languages[field] = {};
    for lang in languages_list.languages['language']:
      # Some values should be collected into an array
      if (p.in_array(field, ['enabled', 'weight'])):
        languages_list.languages[field][lang.field][lang.language] = lang;
      else:
        languages_list.languages[field][lang.field] = lang;
  return languages_list.languages[field];



def language_default(property = None):
  """
   Default language used on the site
  
   @param property
     Optional property of the language object to return
  """
  language_local = variable_get('language_default', p.object_({
    'language' : 'en',
    'name' : 'English',
    'native' : 'English',
    'direction' : 0,
    'enabled' : 1,
    'plurals' : 0,
    'formula' : '',
    'domain' : '',
    'prefix' : '',
    'weight' : 0,
    'javascript' : ''
  }));
  return (getattr(language_local, property) if (property != None) else language_local);


def ip_address():
  """
   If Drupal is behind a reverse proxy, we use the X-Forwarded-For p.header
   instead of p.SERVER['REMOTE_ADDR'], which would be the IP address
   of the proxy server, and not the client's.
  
   @return
     IP address of client machine, adjusted for reverse proxy.
  """
  p.static(ip_address, 'ip_address')
  if (ip_address.ip_address == None):
    ip_address.ip_address = p.SERVER['REMOTE_ADDR'];
    if (variable_get('reverse_proxy', 0) and p.array_key_exists('HTTP_X_FORWARDED_FOR', p.SERVER)):
      # If an array of known reverse proxy IPs is provided, then trust
      # the XFF p.header if request really comes from one of them.
      reverse_proxy_addresses = variable_get('reverse_proxy_addresses', []);
      if (not p.empty(reverse_proxy_addresses) and \
          p.in_array(ip_address.ip_address, reverse_proxy_addresses)):
        # If there are several arguments, we need to check the most
        # recently added one, i.e. the last one.
        ip_address.ip_address = p.array_pop(p.explode(',', p.SERVER['HTTP_X_FORWARDED_FOR']));
  return ip_address.ip_address;


def drupal_function_exists(function):
  """
   @ingroup registry
   @{
  
  
   Confirm that a function is available.
  
   If the function is already available, this function does nothing.
   If the function is not available, it tries to load the file where the
   function lives. If the file is not available, it returns False, so that it
   can be used as a drop-in replacement for p.function_exists().
  
   @param function
     The name of the function to check or load.
   @return
     True if the function is now available, False otherwise.
  """
  p.static(drupal_function_exists, 'checked', [])
  if (p.defined('MAINTENANCE_MODE')):
    return p.function_exists(function)
  if (p.isset(drupal_function_exists.checked, function)):
    return drupal_function_exists.checked[function]
  drupal_function_exists.checked[function] = False
  if (p.function_exists(function)):
    registry_mark_code('function', function)
    drupal_function_exists.checked[function] = True
    return True
  file = db_result(db_query("SELECT filename FROM {registry} WHERE name = '%s' AND type = '%s'", function, 'function'))
  if (file):
    p.require_once(file)
    drupal_function_exists.checked[function] = p.function_exists(function)
    if (drupal_function_exists.checked[function]):
      registry_mark_code('function', function)
  return drupal_function_exists.checked[function]



def drupal_autoload_interface(interface):
  """  
   Confirm that an interface is available.
  
   This function parallels drupal_function_exists(), but is rarely
   called directly. Instead, it is registered as an spl_autoload()
   handler, and PHP calls it for us when necessary.
  
   @param interface
     The name of the interface to check or load.
   @return
     True if the interface is currently available, False otherwise.
  """
  return _registry_check_code('interface', interface)


def drupal_autoload_class(class_):
  """
   Confirm that a class is available.
  
   This function parallels drupal_function_exists(), but is rarely
   called directly. Instead, it is registered as an spl_autoload()
   handler, and PHP calls it for us when necessary.
  
   @param class
     The name of the class to check or load.
   @return
     True if the class is currently available, False otherwise.
  """
  return _registry_check_code('class', class_)


def _registry_check_code(type_, name):
  """
   Helper for registry_check_{interface, class}.
  """
  file = db_result(db_query("SELECT filename FROM {registry} WHERE name = '%s' AND type = '%s'", name, type_))
  if (file):
    p.require_once(file)
    registry_mark_code(type_, name)
    return True


def registry_mark_code(type_, name, return_ = False):
  """
   Collect the resources used for this request.
  
   @param type
     The type of resource.
   @param name
     The name of the resource.
   @param return
     Boolean flag to indicate whether to return the resources.
  """
  p.static(registry_mark_code, 'resources', [])
  if (type_ and name):
    if (not p.isset(registry_mark_code.resources, type_, )):
      registry_mark_code.resources[type_] = []
    if (not p.in_array(name, registry_mark_code.resources[type_])):
      registry_mark_code.resources[type].append( name )
  if (return_):
    return registry_mark_code.resources



def drupal_rebuild_code_registry():
  """
   Rescan all enabled modules and rebuild the registry.
  
   Rescans all code in modules or includes directory, storing a mapping of
   each function, file, and hook implementation in the database.
  """
  p.require_once( './includes/registry.inc' )
  _drupal_rebuild_code_registry()



def registry_cache_hook_implementations(hook, write_to_persistent_cache = False):
  """
   Save hook implementations cache.
  
   @param hook
     Array with the hook name and list of modules that implement it.
   @param write_to_persistent_cache
     Whether to write to the persistent cache.
  """
  p.static(registry_cache_hook_implementations, implementations, {})
  if (hook):
    # Newer is always better, so overwrite anything that's come before.
    registry_cache_hook_implementations.implementations[hook['hook']] = hook['modules']
  if (write_to_persistent_cache == True):
    # Only write this to cache if the implementations data we are going to cache
    # is different to what we loaded earlier in the request.
    if (registry_cache_hook_implementations.implementations != registry_get_hook_implementations_cache()):
      cache_set('hooks', implementations, 'cache_registry');


def registry_cache_path_files():
  """
   Save the files required by the registry for this path.
  """
  used_code = registry_mark_code(None, None, True)
  if (used_code):
    files = []
    type_sql = []
    params = []
    for type,names in used_code.items():
      type_sql.append( "(name IN (" +  db_placeholders(names, 'varchar')  + ") AND type = '%s')" )
      params = p.array_merge(params, names)
      params.append( type )
    res = db_query("SELECT DISTINCT filename FROM {registry} WHERE " +  p.implode(' OR ', type_sql), params)
    while True:
      row = db_fetch_object(res)
      if (row == None):
        break
      files.append( row.filename )
    if (files):
      sort(files);
      # Only write this to cache if the file list we are going to cache
      # is different to what we loaded earlier in the request.
      if (files != registry_load_path_files(True)):
        menu = menu_get_item();
        cache_set('registry:' + menu['path'], p.implode(';', files), 'cache_registry');


def registry_load_path_files(return_ = False):
  """
   registry_load_path_files
  """
  p.static(registry_load_path_files, 'file_cache_data', [])
  if (return_):
    sort(registry_load_path_files.file_cache_data);
    return registry_load_path_files.file_cache_data;
  menu = menu_get_item();
  cache = cache_get('registry:' + menu['path'], 'cache_registry');
  if (not p.empty(cache.data)):
    for file in p.explode(';', cache.data):
      p.require_once(file);
      registry_load_path_files.file_cache_data.append( file );


def registry_get_hook_implementations_cache():
  """
   registry_get_hook_implementations_cache
  """
  p.static(registry_get_hook_implementations_cache, 'implementations')
  if (registry_get_hook_implementations_cache.implementations == None):
    cache = inc_cache.cache_get('hooks', 'cache_registry')
    if (cache):
      registry_get_hook_implementations_cache.implementations = cache.data;
    else:
      registry_get_hook_implementations_cache.implementations = [];
  return registry_get_hook_implementations_cache.implementations;



#
# @} End of "ingroup registry".
#
