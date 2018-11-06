(window.webpackJsonp = window.webpackJsonp || []).push([
    [1], {
        1058: function(module, exports, __webpack_require__) {
            var _ = __webpack_require__(3);
            module.exports = function(obj) {
                obj || (obj = {});
                var __t, __p = "";
                with(obj) __p += '<a href="#" class="appSwitcher__link ' + (null == (__t = className) ? "" : __t) + '" title="' + (null == (__t = tooltip) ? "" : __t) + '">\n    <div class="appSwitcher__linkContent">\n        <div class="appSwitcher__iconShadow appSwitcher__iconShadow--control"></div>\n        <span class="icon ubnt-icon--' + (null == (__t = icon) ? "" : __t) + '"></span>\n    </div>\n    <div class="appSwitcher__itemText">' + (null == (__t = title) ? "" : __t) + "</div>\n</a>\n";
                return __p
            }
        },
        1059: function(t, e, a) {
            "use strict";
            (function(t) {
                Object.defineProperty(e, "__esModule", {
                    value: !0
                });
                var i = s(a(1058));

                function s(t) {
                    return t && t.__esModule ? t : {
                        default: t
                    }
                }
                var n = s(a(34)).default.ItemView.extend({
                    __name__: "ToolItemView",
                    template: i.default,
                    tagName: "li",
                    className: "appSwitcher__item",
                    events: {
                        click: "onClick"
                    },
                    modelEvents: {
                        change: "render"
                    },
                    onClick: function(e) {
                        t(e.target).closest(".appSwitcher").hide(), e.preventDefault(), this.trigger("click")
                    }
                });
                e.default = n
            }).call(this, a(8))
        },
        1060: function(module, exports, __webpack_require__) {
            var _ = __webpack_require__(3);
            module.exports = function(obj) {
                obj || (obj = {});
                var __t, __p = "";
                with(obj) __p += '<div class="appSwitcherButton">\n    <a id="appSwitcherTrigger" href="#" class="appSwitcherButton__trigger"><span class="icon ubnt-icon--tools"></span></a>\n    <div style="display: none" class="appSwitcher appSwitcher--arrow">\n        <ul></ul>\n    </div>\n</div>\n\n';
                return __p
            }
        },
        1061: function(t, e, a) {
            "use strict";
            (function(t) {
                Object.defineProperty(e, "__esModule", {
                    value: !0
                });
                var i = l(a(1060)),
                    s = l(a(581)),
                    n = l(a(1059));

                function l(t) {
                    return t && t.__esModule ? t : {
                        default: t
                    }
                }
                var u = s.default.extend({
                    __name__: "ToolListView",
                    template: i.default,
                    tagName: "div",
                    childViewContainer: function() {
                        return this.ui.toolsContainer = this.ui.toolsContainer.appendTo(document.body), "@ui.toolsList"
                    },
                    childView: n.default,
                    ui: {
                        toolsToggle: "#appSwitcherTrigger",
                        toolsContainer: ".appSwitcher",
                        toolsList: "ul"
                    },
                    getChildView: function() {
                        return n.default
                    },
                    hideList: function() {
                        this.ui.toolsContainer.slideUp(200)
                    },
                    toggleList: function() {
                        this.ui.toolsContainer.slideToggle(200)
                    },
                    setContainerPosition: function() {
                        this.ui.toolsContainer.css("left", this.ui.toolsToggle.offset().left - this.ui.toolsContainer[0].getBoundingClientRect().width + 45)
                    },
                    onRender: function() {
                        var e = this;
                        this.ui.toolsToggle.on("click", function(t) {
                            t.preventDefault(), e.toggleList(), e.setContainerPosition()
                        });
                        t(window).resize(function() {
                            clearTimeout(void 0), setTimeout(function() {
                                return e.setContainerPosition()
                            }, 10)
                        }), t(document).on("click", function(a) {
                            var i = t(a.target);
                            0 === i.closest(e.ui.toolsToggle).length && 0 === i.closest(e.ui.toolsContainer).length && e.hideList()
                        })
                    }
                });
                e.default = u
            }).call(this, a(8))
        },
        1062: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = n(a(582)),
                s = n(a(1061));

            function n(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }
            var l = i.default.extend({
                __name__: "ToolController",
                listView: s.default
            });
            e.default = l
        },
        1063: function(module, exports, __webpack_require__) {
            var _ = __webpack_require__(3);
            module.exports = function(obj) {
                obj || (obj = {});
                var __t, __p = "";
                with(obj) __p += " " + (null == (__t = title) ? "" : __t) + "\n\n\n";
                return __p
            }
        },
        1064: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = s(a(1063));

            function s(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }
            var n = s(a(34)).default.ItemView.extend({
                __name__: "TabsItemView",
                template: i.default,
                tagName: "li",
                className: "tabs__item",
                events: {
                    click: "onClick"
                },
                modelEvents: {
                    change: "render"
                },
                onClick: function(t) {
                    this.trigger("click")
                },
                onRender: function() {
                    this.$el.toggleClass("is-tab-selected", this.model.get("isActive"))
                },
                onShow: function() {}
            });
            e.default = n
        },
        1065: function(module, exports, __webpack_require__) {
            var _ = __webpack_require__(3);
            module.exports = function(obj) {
                obj || (obj = {});
                var __t, __p = "";
                with(obj) __p += "";
                return __p
            }
        },
        1066: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = l(a(1065)),
                s = l(a(581)),
                n = l(a(1064));

            function l(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }
            var u = s.default.extend({
                __name__: "TabsView",
                template: i.default,
                tagName: "ul",
                className: "appTabs",
                childViewContainer: null,
                childView: n.default,
                getChildView: function() {
                    return n.default
                }
            });
            e.default = u
        },
        1067: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = n(a(582)),
                s = n(a(1066));

            function n(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }
            var l = i.default.extend({
                __name__: "TabsController",
                listView: s.default
            });
            e.default = l
        },
        1068: function(module, exports, __webpack_require__) {
            var _ = __webpack_require__(3);
            module.exports = function(obj) {
                obj || (obj = {});
                var __t, __p = "";
                with(obj) __p += '<a href="#' + (null == (__t = url) ? "" : __t) + '">\n    <div class="iconText appIconText">\n        <span class="iconText__icon icon ubnt-icon--' + (null == (__t = icon) ? "" : __t) + '"></span><span class="iconText__text">' + (null == (__t = title) ? "" : __t) + "</span>\n    </div>\n</a>\n";
                return __p
            }
        },
        1069: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = s(a(1068));

            function s(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }
            var n = s(a(635)).default.extend({
                __name__: "NavigationLinkViewMobile",
                template: i.default,
                tagName: "li"
            });
            e.default = n
        },
        1070: function(module, exports, __webpack_require__) {
            var _ = __webpack_require__(3);
            module.exports = function(obj) {
                obj || (obj = {});
                var __t, __p = "";
                with(obj) __p += '<a class="appGlobalSideNav__item" href="#' + (null == (__t = url) ? "" : __t) + '">\n    <div class="appGlobalSideNav__itemIcon icon ubnt-icon--' + (null == (__t = icon) ? "" : __t) + '"></div>\n    <div class="appGlobalSideNavTooltip">' + (null == (__t = title) ? "" : __t) + "</div>\n</a>\n\n\n";
                return __p
            }
        },
        1071: function(module, exports, __webpack_require__) {
            var _ = __webpack_require__(3);
            module.exports = function(obj) {
                obj || (obj = {});
                var __t, __p = "";
                with(obj) __p += '<div class="iconText appIconText">\n    <span class="iconText__icon icon ubnt-icon--' + (null == (__t = icon) ? "" : __t) + '"></span><span class="iconText__text">' + (null == (__t = title) ? "" : __t) + "</span>\n</div>\n";
                return __p
            }
        },
        1072: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = s(a(1071));

            function s(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }
            var n = s(a(636)).default.extend({
                __name__: "NavigationItemViewMobile",
                template: i.default,
                tagName: "li"
            });
            e.default = n
        },
        1073: function(module, exports, __webpack_require__) {
            var _ = __webpack_require__(3);
            module.exports = function(obj) {
                obj || (obj = {});
                var __t, __p = "";
                with(obj) __p += '<div class="appGlobalSideNav__item">\n    <div class="appGlobalSideNav__itemIcon icon ubnt-icon--' + (null == (__t = icon) ? "" : __t) + '"></div>\n    <div class="appGlobalSideNavTooltip">' + (null == (__t = title) ? "" : __t) + "</div>\n</div>\n\n\n";
                return __p
            }
        },
        1074: function(module, exports, __webpack_require__) {
            var _ = __webpack_require__(3);
            module.exports = function(obj) {
                obj || (obj = {});
                var __t, __p = "";
                with(obj) __p += '<ul class="navigation_list"></ul>\n';
                return __p
            }
        },
        1075: function(t, e, a) {
            "use strict";
            (function(t) {
                Object.defineProperty(e, "__esModule", {
                    value: !0
                });
                var i = s(a(637));

                function s(t) {
                    return t && t.__esModule ? t : {
                        default: t
                    }
                }
                var n = s(a(9)).default.Collection.extend({
                    __name__: "NavigationList",
                    model: i.default,
                    comparator: "position",
                    getActive: function() {
                        return this.findWhere({
                            isActive: !0
                        })
                    },
                    toggleActive: function(e, a) {
                        t.each(this.models, function(t) {
                            t.set("isActive", !1)
                        }, this), e.isStateful() && e.set("isActive", a)
                    },
                    getByUrl: function(t) {
                        return this.findWhere({
                            url: t
                        })
                    }
                });
                e.default = n
            }).call(this, a(3))
        },
        1076: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = l(a(38)),
                s = l(a(34)),
                n = l(a(638));

            function l(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }
            var u = s.default.LayoutView.extend({
                __name__: "RootView",
                el: "body",
                events: {
                    "click a.airosLogout": function() {
                        i.default.commands.execute("session:logout")
                    }
                },
                regions: {
                    regionMain: "#main_region",
                    dialogRegion: n.default.extend({
                        el: "#dialog_region"
                    })
                }
            });
            e.default = u
        },
        1077: function(t, e, a) {
            "use strict";
            var i, s, n, l = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function(t) {
                return typeof t
            } : function(t) {
                return t && "function" == typeof Symbol && t.constructor === Symbol && t !== Symbol.prototype ? "symbol" : typeof t
            };
            s = [a(8)], void 0 === (n = "function" == typeof(i = function(t) {
                var e = "pushy",
                    a = {};

                function i(i, s) {
                    this.element = i, this.options = t.extend({}, a, s), this._defaults = a, this._name = e, this.pushy = t(".pushy"), this.body = t("body"), this.container = t(".pushy_container"), this.push = t(".push"), this.siteOverlay = t(".pushy_overlay"), this.pushyClass = "pushy-left pushy-open", this.pushyActiveClass = "pushy-active", this.containerClass = "container-push", this.pushClass = "push-push", this.menuBtn = t(".menu_button"), this.menuSpeed = 200, this.menuWidth = this.pushy.width() + "px", this.state = !0, this._init()
                }
                i.prototype = {
                    _togglePushy: function() {
                        this.body.toggleClass(this.pushyActiveClass), this.pushy.toggleClass(this.pushyClass), this.container.toggleClass(this.containerClass), this.push.toggleClass(this.pushClass)
                    },
                    _closePushy: function() {
                        this.body.removeClass(this.pushyActiveClass), this.pushy.removeClass(this.pushyClass), this.container.removeClass(this.containerClass), this.push.removeClass(this.pushClass)
                    },
                    _openPushyFallback: function() {
                        this.body.addClass(this.pushyActiveClass), this.pushy.animate({
                            left: "0px"
                        }, this.menuSpeed), this.container.animate({
                            left: this.menuWidth
                        }, this.menuSpeed), this.push.animate({
                            left: this.menuWidth
                        }, this.menuSpeed)
                    },
                    _closePushyFallback: function() {
                        this.body.removeClass(this.pushyActiveClass), this.pushy.animate({
                            left: "-" + this.menuWidth
                        }, this.menuSpeed), this.container.animate({
                            left: "0px"
                        }, this.menuSpeed), this.push.animate({
                            left: "0px"
                        }, this.menuSpeed)
                    },
                    _init: function() {
                        var t = this;
                        this.menuBtn.click(function() {
                            t._togglePushy()
                        }), this.siteOverlay.click(function() {
                            t._togglePushy()
                        })
                    },
                    close: function() {
                        this._togglePushy()
                    }
                }, t.fn[e] = function(a) {
                    var s, n;
                    if (this.data("plugin_" + e) instanceof i || this.data("plugin_" + e, new i(this, a)), (n = this.data("plugin_" + e)).element = this, void 0 === a || "object" === (void 0 === a ? "undefined" : l(a))) "function" == typeof n.init && n.init(a);
                    else {
                        if ("string" == typeof a && "function" == typeof n[a]) return s = Array.prototype.slice.call(arguments, 1), n[a].apply(n, s);
                        t.error("Method " + a + " does not exist on jQuery." + e)
                    }
                }
            }) ? i.apply(e, s) : i) || (t.exports = n)
        },
        1078: function(module, exports, __webpack_require__) {
            var _ = __webpack_require__(3);
            module.exports = function(obj) {
                obj || (obj = {});
                var __t, __p = "";
                with(obj) __p += '<div class="pushy pushy-left">\n    <div class="logo_wrapper">\n        <span class="icon ubnt-icon--airOS8 logo-airos"></span>\n    </div>\n    <div id="mob_navigation_main"></div>\n</div>\n\n<div class="pushy_overlay"></div>\n\n<div class="pushy_container">\n    <div class="header">\n        <span class="menu_button icon ubnt-icon--menu"></span>\n    </div>\n    <div id="alert_container" class="noty-container"></div>\n    <div id="mob_content"></div>\n</div>\n';
                return __p
            }
        },
        1079: function(t, e, a) {
            "use strict";
            (function(t) {
                Object.defineProperty(e, "__esModule", {
                    value: !0
                });
                var i = n(a(1078)),
                    s = n(a(34));

                function n(t) {
                    return t && t.__esModule ? t : {
                        default: t
                    }
                }
                a(1077);
                var l = s.default.LayoutView.extend({
                    template: i.default,
                    regions: {
                        regionContent: "#mob_content",
                        regionMainMenu: "#mob_navigation_main"
                    },
                    ui: {
                        content: "#mob_content"
                    },
                    closeMenu: function() {
                        this.$el.pushy("close")
                    },
                    onShow: function() {
                        t("html").addClass("mobile_layout"), t("body").addClass("mobile_layout"), this.$el.pushy()
                    },
                    onDestroy: function() {
                        t("html").removeClass("mobile_layout"), t("body").removeClass("mobile_layout")
                    }
                });
                e.default = l
            }).call(this, a(8))
        },
        1080: function(module, exports, __webpack_require__) {
            var _ = __webpack_require__(3);
            module.exports = function(obj) {
                obj || (obj = {});
                var __t, __p = "";
                with(obj) __p += '<div class="appGlobalHeader">\n    <div class="appGlobalHeader__content appGlobalHeader__content--left">\n        <a href="//ubnt.com" title="' + (null == (__t = __("Visit ubnt.com")) ? "" : __t) + '" target="_blank" class="appGlobalHeader__ubntLogo">\n            <div class="appGlobalHeader__ubntLogoInner">\n                <div class="icon ubnt-icon--ubnt-logo-u"></div>\n            </div>\n        </a>\n        <div class="appGlobalHeader__logo">\n            <div class="icon ubnt-icon--airOS8 logo-airos"></div>\n        </div>\n        <div class="appGlobalHeader__version">\n            <div class="appGlobalHeader__versionItem"></div>\n        </div>\n    </div>\n\n    <div class="appGlobalHeader__content appGlobalHeader__content--right">\n        <span style="display: none" class="ubnt-icon ubnt-icon--book-2 walkme-icon" title="' + (null == (__t = __("Training")) ? "" : __t) + '"></span>\n\n        <div id="devIndicator"><span>DEV MODE</span></div>\n\n        <div class="unmsIndicator">\n            <a id="unmsLink" target="_blank" href="' + (null == (__t = unmsLink) ? "" : __t) + '">\n                <img id="unmsState" src="' + (null == (__t = unmsState) ? "" : __t) + '">\n            </a>\n        </div>\n\n        <div id="tools_menu" title="' + (null == (__t = __("Tools")) ? "" : __t) + '"></div>\n    </div>\n\n    <div class="appAccountLinks">\n        <a href="#" title="' + (null == (__t = __("Logout")) ? "" : __t) + '" class="airosLogout"><span class="icon ubnt-icon--logout"></span></a>\n    </div>\n</div>\n\n<div class="appGlobalSideNav">\n    <div id="main_menu" class="appGlobalSideNav__primaryMenu"></div>\n    <div id="secondary_menu" class="appGlobalSideNav__secondaryMenu"></div>\n</div>\n\n<div id="alert_container" class="noty-container appToastContainer"></div>\n<div id="content_wrapper" class="desktopLayout"></div>\n\n';
                return __p
            }
        },
        1081: function(t, e, a) {
            "use strict";
            (function(t) {
                Object.defineProperty(e, "__esModule", {
                    value: !0
                });
                var i = u(a(38)),
                    s = u(a(1080)),
                    n = u(a(34)),
                    l = u(a(583));

                function u(t) {
                    return t && t.__esModule ? t : {
                        default: t
                    }
                }

                function o(t) {
                    var e = t ? "https://cdn.walkme.com/users/b990f147cb7b49558f7a9f91454f4017/test/walkme_b990f147cb7b49558f7a9f91454f4017_https.js" : "https://cdn.walkme.com/users/b990f147cb7b49558f7a9f91454f4017/walkme_b990f147cb7b49558f7a9f91454f4017_https.js",
                        a = document.createElement("script");
                    a.type = "text/javascript", a.async = !0, a.src = e;
                    var i = document.getElementsByTagName("script")[0];
                    i.parentNode.insertBefore(a, i), window._walkmeConfig = {
                        smartLoad: !0
                    }
                }
                var r = n.default.LayoutView.extend({
                    __name__: "DesktopLayout",
                    template: s.default,
                    regions: {
                        regionContent: "#content_wrapper",
                        regionMainMenu: "#main_menu",
                        regionSecondaryMenu: "#secondary_menu",
                        regionTools: "#tools_menu"
                    },
                    ui: {
                        content: "#content_wrapper",
                        deviceNameAndVersion: ".appGlobalHeader__versionItem",
                        walkmeIcon: ".walkme-icon",
                        unmsLink: "#unmsLink",
                        unmsState: "#unmsState",
                        devIndicator: "#devIndicator"
                    },
                    events: {
                        "click @ui.walkmeIcon": "redirectToSSO"
                    },
                    onRender: function() {
                        this.listenTo(i.default.vent, "app:started", function() {
                            this.fillDeviceModelAndVersion()
                        }), this.listenTo(i.default.vent, "status:updated", function() {
                            this.updateUnmsInfo()
                        }), this.listenTo(i.default.vent, "navigate:on_action", function(t) {
                            this.pageTitle = t.get("title"), this.ui.devIndicator.toggle(i.default.settings.isDevMode())
                        }), this.listenTo(i.default.vent, "navigate:route_action navigate:on_select", function() {
                            l.default.disableAutocomplete(), l.default.disableLastPass()
                        }), window.SA && this.initWalkme()
                    },
                    initialize: function() {
                        this.model = new Backbone.Model({
                            unmsLink: "https://unms.com",
                            unmsState: "images/unms-grey.svg"
                        })
                    },
                    redirectToSSO: function() {
                        var e = -1 != window.location.href.indexOf("dev-") || -1 != window.location.href.indexOf("stg-");
                        i.default.execute("show_confirmation_dialog", {
                            headerTitle: __("Training"),
                            contentHtml: __("Please sign in to use the AirOS Training Center. This will allow you to save your progress."),
                            yesButtonText: __("Sign In"),
                            action: function() {
                                return t.ajax({
                                    url: e ? "https://sso-stage.ubnt.com/api/sso/v1/user/self" : "https://sso.ubnt.com/api/sso/v1/user/self",
                                    type: "GET",
                                    crossDomain: !0,
                                    dataType: "json",
                                    cache: !1,
                                    xhrFields: {
                                        withCredentials: !0
                                    },
                                    complete: function(t) {
                                        200 != t.status ? window.location.href = (e ? "//staging-account.ubnt.com/login?redirect=" : "//account.ubnt.com/login?redirect=") + encodeURI(window.location.href) : o(e)
                                    }
                                }), !0
                            }
                        })
                    },
                    initWalkme: function() {
                        var e = -1 != window.location.href.indexOf("dev-") || -1 != window.location.href.indexOf("stg-"),
                            a = this;
                        t.ajax({
                            url: e ? "https://sso-stage.ubnt.com/api/sso/v1/user/self" : "https://sso.ubnt.com/api/sso/v1/user/self",
                            type: "GET",
                            crossDomain: !0,
                            dataType: "json",
                            cache: !1,
                            xhrFields: {
                                withCredentials: !0
                            },
                            complete: function(t) {
                                200 != t.status ? a.ui.walkmeIcon.show() : o(e)
                            }
                        })
                    },
                    fillDeviceModelAndVersion: function() {
                        this.ui.deviceNameAndVersion.text(_uesc(i.default.status.getDeviceModel()) + " | " + i.default.status.getFirmwareVersion())
                    },
                    updateUnmsInfo: function() {
                        var t = i.default.status.getProperty(i.default.status.UNMS),
                            e = "images/unms-";
                        switch (t.get("status")) {
                            case 0:
                                e += "grey.svg";
                                break;
                            case 2:
                                e += "green.svg";
                                break;
                            default:
                                e += -1 == this.ui.unmsState.attr("src").indexOf("no") ? "no.svg" : "yellow.svg"
                        }
                        this.ui.unmsLink.attr("href", t.get("link")), this.ui.unmsState.attr("src", e)
                    }
                });
                e.default = r
            }).call(this, a(8))
        },
        1082: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = function(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }(a(9)).default.Model.extend({
                __name__: "InterfaceStatusModel"
            });
            e.default = i
        },
        1083: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = n(a(9)),
                s = n(a(1082));

            function n(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }
            var l = i.default.Collection.extend({
                __name__: "InterfaceStatusCollection",
                model: s.default
            });
            e.default = l
        },
        1084: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = function(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }(a(9));
            e.default = i.default.Model.extend({
                __name__: "AirCubeModel",
                defaults: {
                    essid: null,
                    wmode: null,
                    product: null,
                    hwaddr: null,
                    uptime: null,
                    hostname: null,
                    addresses: null,
                    fwversion: null,
                    ipv4: null
                }
            })
        },
        1085: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = n(a(9)),
                s = n(a(1084));

            function n(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }
            e.default = i.default.Collection.extend({
                __name__: "AirCubeCollection",
                model: s.default
            })
        },
        1086: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = function(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }(a(9)).default.Model.extend({
                __name__: "StationModel",
                defaults: {
                    mac: null,
                    properties: null,
                    data: null
                }
            });
            e.default = i
        },
        1087: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = s(a(1086));

            function s(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }
            var n = s(a(9)).default.Collection.extend({
                __name__: "StationCollection",
                model: i.default,
                findByMac: function(t) {
                    return this.findWhere({
                        mac: t
                    })
                }
            });
            e.default = n
        },
        1088: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = s(a(639));

            function s(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }
            var n = s(a(9)).default.Collection.extend({
                __name__: "PropertyCollection",
                model: i.default
            });
            e.default = n
        },
        418: function(t, e, a) {
            "use strict";
            (function(t) {
                Object.defineProperty(e, "__esModule", {
                    value: !0
                });
                var i = n(a(31)),
                    s = n(a(3));

                function n(t) {
                    return t && t.__esModule ? t : {
                        default: t
                    }
                }
                var l = function(t) {
                    this.options = s.default.extend({}, t), s.default.defaults(this.options, {
                        duration: 1e3
                    })
                };
                l.prototype.start = function(e, a) {
                    var n = this,
                        l = {
                            discover: "y",
                            duration: e || this.options.duration,
                            filter_aircube: a
                        };
                    return s.default.isUndefined(this.options.targetIp) || (l.host = this.options.targetIp), new t.Deferred(function(e) {
                        t.ajax({
                            type: "POST",
                            url: i.default.getDiscoveryUrl(),
                            dataType: "json",
                            timeout: n.options.duration + 5e3,
                            data: l
                        }).done(function(t, a, i) {
                            _escObj(t), e.resolve(t.devices)
                        }).fail(function(t, a, i) {
                            e.reject()
                        })
                    }).promise()
                }, l.prototype.startAirCubeLookup = function(t, e) {
                    var a = setTimeout(function() {
                        return this.start(1e3, 1).then(function(e) {
                            t(e), clearTimeout(a), this.startAirCubeLookup(t)
                        }.bind(this))
                    }.bind(this), e || 6e4)
                }, e.default = l
            }).call(this, a(8))
        },
        556: function(t, e, a) {
            "use strict";
            var i = r(a(38)),
                s = r(a(31)),
                n = r(a(582)),
                l = r(a(1067)),
                u = r(a(1062)),
                o = r(a(9));

            function r(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }(function() {
                var t = {};
                t[s.default.NavigationGroups.PRIMARY] = new n.default, t[s.default.NavigationGroups.SECONDARY] = new n.default, t[s.default.NavigationGroups.SETTINGS] = new l.default, t[s.default.NavigationGroups.TOOLS] = new u.default, i.default.navigation = {
                    back: function() {
                        o.default.history.history.back()
                    },
                    openPage: function(t) {
                        o.default.history.navigate(t, {
                            trigger: !0
                        })
                    },
                    replacePage: function(t) {
                        o.default.history.navigate(t, {
                            trigger: !0,
                            replace: !0
                        })
                    },
                    getSettingsNavigationView: function() {
                        var e = t[s.default.NavigationGroups.SETTINGS].getView();
                        return e && e.isDestroyed && (e = t[s.default.NavigationGroups.SETTINGS].initializeView()), e
                    },
                    setDocumentTitle: function(t) {
                        document.title = _uesc(i.default.status.getValue(i.default.status.DEVICE_NAME)) + " - " + t + " - airOS"
                    }
                }, i.default.navigation.addItem = function(e, a) {
                    t[e].addItem(a)
                }, i.default.navigation.removeItem = function(e, a) {
                    t[e].removeItem(a)
                }, i.default.navigation.updateItem = function(e, a) {
                    t[e].updateItem(a)
                }, i.default.layout.regionMainMenu.show(t[s.default.NavigationGroups.PRIMARY].getView()), i.default.settings.isDesktopLayout() && (i.default.layout.regionSecondaryMenu.show(t[s.default.NavigationGroups.SECONDARY].getView()), i.default.layout.regionTools.show(t[s.default.NavigationGroups.TOOLS].getView())), i.default.navigation.groups = t, i.default.vent.trigger("navigation:initialized"), i.default.vent.on("app:started", function() {
                    if (t[s.default.NavigationGroups.SETTINGS].list.getActive()) {
                        var e = t[s.default.NavigationGroups.PRIMARY].list.getByUrl("settings");
                        t[s.default.NavigationGroups.PRIMARY].list.toggleActive(e, !0)
                    }
                })
            })()
        },
        557: function(t, e, a) {
            "use strict";
            (function(t, e) {
                var i = r(a(38)),
                    s = r(a(1081)),
                    n = r(a(1079)),
                    l = r(a(1076)),
                    u = r(a(34)),
                    o = r(a(638));

                function r(t) {
                    return t && t.__esModule ? t : {
                        default: t
                    }
                }
                a(56);
                var _ = {
                    switchToMobileLayout: function() {
                        i.default.settings.isMobileLayout() ? i.default.navigation.openPage("dashboard") : (UBNT.Utils.Storage.set("ui_layout", i.default.settings.LayoutTypes.MOBILE), i.default.reload())
                    },
                    switchToDesktopLayout: function() {
                        i.default.settings.isDesktopLayout() ? i.default.navigation.openPage("dashboard") : (UBNT.Utils.Storage.set("ui_layout", i.default.settings.LayoutTypes.DESKTOP), i.default.reload())
                    },
                    init: function() {
                        switch (this.listenVisibilityChanges(), i.default.rootView = new l.default, i.default.dialogRegion = i.default.rootView.dialogRegion, parseInt(UBNT.Utils.Storage.get("ui_layout"))) {
                            case i.default.settings.LayoutTypes.MOBILE:
                                i.default.settings.setLayout(i.default.settings.LayoutTypes.MOBILE);
                                break;
                            case i.default.settings.LayoutTypes.DESKTOP:
                                i.default.settings.setLayout(i.default.settings.LayoutTypes.DESKTOP);
                                break;
                            default:
                                i.default.settings.setLayout(i.default.settings.LayoutTypes.AUTO)
                        }
                        if (i.default.settings.isMobileLayout()) {
                            var a = new n.default;
                            a.listenTo(i.default.vent, "navigate:on_select", function() {
                                a.closeMenu()
                            }), i.default.layout = a
                        } else i.default.layout = new s.default;
                        i.default.rootView.regionMain.show(i.default.layout), i.default.vent.on("navigation:initialized", function() {
                            new(u.default.AppRouter.extend({
                                appRoutes: {
                                    mobile: "switchToMobileLayout",
                                    desktop: "switchToDesktopLayout"
                                }
                            }))({
                                controller: _
                            }), UBNT.Utils.Platform.isMobile() && (i.default.settings.isMobileLayout() ? (t("body").addClass("mobile_platform " + UBNT.Utils.Platform.getPlatformString()), t("html").addClass("mobile_platform " + UBNT.Utils.Platform.getPlatformString()), i.default.navigation.addItem(i.default.settings.NavigationGroups.SECONDARY, {
                                name: "layout",
                                title: __("Desktop Version"),
                                icon: "layout",
                                url: "desktop",
                                position: 7,
                                openAction: function() {
                                    _.switchToDesktopLayout()
                                }
                            })) : i.default.navigation.addItem(i.default.settings.NavigationGroups.SECONDARY, {
                                name: "layout",
                                title: __("Mobile Version"),
                                icon: "layout",
                                url: "mobile",
                                position: 7,
                                openAction: function() {
                                    _.switchToMobileLayout()
                                }
                            }))
                        }), i.default.commands.setHandler("show_dynamic_dialog", function(a, s, n) {
                            if (n && s && i.default.openDialogs && i.default.openDialogs[s]) t("#" + i.default.openDialogs[s]).dialog("moveToTop");
                            else {
                                var l = e.uniqueId("dlg");
                                t("<div/>", {
                                    id: l
                                }).appendTo(t("#dynamic_dialogs")), (new(o.default.extend({
                                    el: "#" + l,
                                    onDestroy: function() {
                                        t("#" + l).remove()
                                    }
                                }))).show(a), s && (i.default.openDialogs || (i.default.openDialogs = {}), i.default.openDialogs[s] = l)
                            }
                        }), i.default.commands.setHandler("close_dynamic_dialog", function(e) {
                            i.default.openDialogs && i.default.openDialogs[e] && t("#" + i.default.openDialogs[e]).dialog("close")
                        }), i.default.commands.setHandler("show_confirmation_dialog", function(t) {
                            var a = new u.default.ItemView;
                            a.template = e.template(t.contentHtml), a.dialogOptions = function() {
                                return {
                                    title: t.headerTitle,
                                    dialogClass: "ui-dialog-white",
                                    width: 440,
                                    height: 170,
                                    modal: !0,
                                    buttons: [{
                                        text: t.noButtonText,
                                        class: "appMainButton appMainButton--transparent",
                                        danger: !0,
                                        click: function() {
                                            a.trigger("dialog:close")
                                        }
                                    }, {
                                        text: t.yesButtonText,
                                        primary: !0,
                                        class: "appMainButton appMainButton--cozy appMainButton--primary",
                                        click: function() {
                                            t.action() && a.trigger("dialog:close")
                                        }
                                    }]
                                }
                            }, i.default.execute("show_dynamic_dialog", a)
                        })
                    },
                    listenVisibilityChanges: function() {
                        var t = "hidden";

                        function e(e) {
                            var a = "visible",
                                s = "hidden",
                                n = {
                                    focus: a,
                                    focusin: a,
                                    pageshow: a,
                                    blur: s,
                                    focusout: s,
                                    pagehide: s
                                };
                            (e = e || window.event).type in n ? i.default.isVisible = "visible" === n[e.type] : i.default.isVisible = !this[t], i.default.vent.trigger("app:visibility:change", i.default.isVisible)
                        }
                        t in document ? document.addEventListener("visibilitychange", e) : (t = "mozHidden") in document ? document.addEventListener("mozvisibilitychange", e) : (t = "webkitHidden") in document ? document.addEventListener("webkitvisibilitychange", e) : (t = "msHidden") in document ? document.addEventListener("msvisibilitychange", e) : "onfocusin" in document ? document.onfocusin = document.onfocusout = e : window.onpageshow = window.onpagehide = window.onfocus = window.onblur = e, void 0 !== document[t] && e({
                            type: document[t] ? "blur" : "focus"
                        })
                    }
                };
                _.init()
            }).call(this, a(8), a(3))
        },
        558: function(t, e, a) {
            var i = {
                "./af": 541,
                "./af.js": 541,
                "./ar": 540,
                "./ar-dz": 539,
                "./ar-dz.js": 539,
                "./ar-kw": 538,
                "./ar-kw.js": 538,
                "./ar-ly": 537,
                "./ar-ly.js": 537,
                "./ar-ma": 536,
                "./ar-ma.js": 536,
                "./ar-sa": 535,
                "./ar-sa.js": 535,
                "./ar-tn": 534,
                "./ar-tn.js": 534,
                "./ar.js": 540,
                "./az": 533,
                "./az.js": 533,
                "./be": 532,
                "./be.js": 532,
                "./bg": 531,
                "./bg.js": 531,
                "./bm": 530,
                "./bm.js": 530,
                "./bn": 529,
                "./bn.js": 529,
                "./bo": 528,
                "./bo.js": 528,
                "./br": 527,
                "./br.js": 527,
                "./bs": 526,
                "./bs.js": 526,
                "./ca": 525,
                "./ca.js": 525,
                "./cs": 524,
                "./cs.js": 524,
                "./cv": 523,
                "./cv.js": 523,
                "./cy": 522,
                "./cy.js": 522,
                "./da": 521,
                "./da.js": 521,
                "./de": 520,
                "./de-at": 519,
                "./de-at.js": 519,
                "./de-ch": 518,
                "./de-ch.js": 518,
                "./de.js": 520,
                "./dv": 517,
                "./dv.js": 517,
                "./el": 516,
                "./el.js": 516,
                "./en-au": 515,
                "./en-au.js": 515,
                "./en-ca": 514,
                "./en-ca.js": 514,
                "./en-gb": 513,
                "./en-gb.js": 513,
                "./en-ie": 512,
                "./en-ie.js": 512,
                "./en-il": 511,
                "./en-il.js": 511,
                "./en-nz": 510,
                "./en-nz.js": 510,
                "./eo": 509,
                "./eo.js": 509,
                "./es": 508,
                "./es-do": 507,
                "./es-do.js": 507,
                "./es-us": 506,
                "./es-us.js": 506,
                "./es.js": 508,
                "./et": 505,
                "./et.js": 505,
                "./eu": 504,
                "./eu.js": 504,
                "./fa": 503,
                "./fa.js": 503,
                "./fi": 502,
                "./fi.js": 502,
                "./fo": 501,
                "./fo.js": 501,
                "./fr": 500,
                "./fr-ca": 499,
                "./fr-ca.js": 499,
                "./fr-ch": 498,
                "./fr-ch.js": 498,
                "./fr.js": 500,
                "./fy": 497,
                "./fy.js": 497,
                "./gd": 496,
                "./gd.js": 496,
                "./gl": 495,
                "./gl.js": 495,
                "./gom-latn": 494,
                "./gom-latn.js": 494,
                "./gu": 493,
                "./gu.js": 493,
                "./he": 492,
                "./he.js": 492,
                "./hi": 491,
                "./hi.js": 491,
                "./hr": 490,
                "./hr.js": 490,
                "./hu": 489,
                "./hu.js": 489,
                "./hy-am": 488,
                "./hy-am.js": 488,
                "./id": 487,
                "./id.js": 487,
                "./is": 486,
                "./is.js": 486,
                "./it": 485,
                "./it.js": 485,
                "./ja": 484,
                "./ja.js": 484,
                "./jv": 483,
                "./jv.js": 483,
                "./ka": 482,
                "./ka.js": 482,
                "./kk": 481,
                "./kk.js": 481,
                "./km": 480,
                "./km.js": 480,
                "./kn": 479,
                "./kn.js": 479,
                "./ko": 478,
                "./ko.js": 478,
                "./ky": 477,
                "./ky.js": 477,
                "./lb": 476,
                "./lb.js": 476,
                "./lo": 475,
                "./lo.js": 475,
                "./lt": 474,
                "./lt.js": 474,
                "./lv": 473,
                "./lv.js": 473,
                "./me": 472,
                "./me.js": 472,
                "./mi": 471,
                "./mi.js": 471,
                "./mk": 470,
                "./mk.js": 470,
                "./ml": 469,
                "./ml.js": 469,
                "./mn": 468,
                "./mn.js": 468,
                "./mr": 467,
                "./mr.js": 467,
                "./ms": 466,
                "./ms-my": 465,
                "./ms-my.js": 465,
                "./ms.js": 466,
                "./mt": 464,
                "./mt.js": 464,
                "./my": 463,
                "./my.js": 463,
                "./nb": 462,
                "./nb.js": 462,
                "./ne": 461,
                "./ne.js": 461,
                "./nl": 460,
                "./nl-be": 459,
                "./nl-be.js": 459,
                "./nl.js": 460,
                "./nn": 458,
                "./nn.js": 458,
                "./pa-in": 457,
                "./pa-in.js": 457,
                "./pl": 456,
                "./pl.js": 456,
                "./pt": 455,
                "./pt-br": 454,
                "./pt-br.js": 454,
                "./pt.js": 455,
                "./ro": 453,
                "./ro.js": 453,
                "./ru": 452,
                "./ru.js": 452,
                "./sd": 451,
                "./sd.js": 451,
                "./se": 450,
                "./se.js": 450,
                "./si": 449,
                "./si.js": 449,
                "./sk": 448,
                "./sk.js": 448,
                "./sl": 447,
                "./sl.js": 447,
                "./sq": 446,
                "./sq.js": 446,
                "./sr": 445,
                "./sr-cyrl": 444,
                "./sr-cyrl.js": 444,
                "./sr.js": 445,
                "./ss": 443,
                "./ss.js": 443,
                "./sv": 442,
                "./sv.js": 442,
                "./sw": 441,
                "./sw.js": 441,
                "./ta": 440,
                "./ta.js": 440,
                "./te": 439,
                "./te.js": 439,
                "./tet": 438,
                "./tet.js": 438,
                "./tg": 437,
                "./tg.js": 437,
                "./th": 436,
                "./th.js": 436,
                "./tl-ph": 435,
                "./tl-ph.js": 435,
                "./tlh": 434,
                "./tlh.js": 434,
                "./tr": 433,
                "./tr.js": 433,
                "./tzl": 432,
                "./tzl.js": 432,
                "./tzm": 431,
                "./tzm-latn": 430,
                "./tzm-latn.js": 430,
                "./tzm.js": 431,
                "./ug-cn": 429,
                "./ug-cn.js": 429,
                "./uk": 428,
                "./uk.js": 428,
                "./ur": 427,
                "./ur.js": 427,
                "./uz": 426,
                "./uz-latn": 425,
                "./uz-latn.js": 425,
                "./uz.js": 426,
                "./vi": 424,
                "./vi.js": 424,
                "./x-pseudo": 423,
                "./x-pseudo.js": 423,
                "./yo": 422,
                "./yo.js": 422,
                "./zh-cn": 421,
                "./zh-cn.js": 421,
                "./zh-hk": 420,
                "./zh-hk.js": 420,
                "./zh-tw": 419,
                "./zh-tw.js": 419
            };

            function s(t) {
                var e = n(t);
                return a(e)
            }

            function n(t) {
                var e = i[t];
                if (!(e + 1)) {
                    var a = new Error("Cannot find module '" + t + "'");
                    throw a.code = "MODULE_NOT_FOUND", a
                }
                return e
            }
            s.keys = function() {
                return Object.keys(i)
            }, s.resolve = n, t.exports = s, s.id = 558
        },
        559: function(t, e, a) {
            "use strict";
            (function(t) {
                Object.defineProperty(e, "__esModule", {
                    value: !0
                });
                var i = g(a(38)),
                    s = g(a(31)),
                    n = g(a(1088)),
                    l = g(a(1087)),
                    u = g(a(1085)),
                    o = g(a(9)),
                    r = g(a(102)),
                    _ = g(a(572)),
                    d = g(a(1083)),
                    c = g(a(74)),
                    h = g(a(0)),
                    f = g(a(3));

                function g(t) {
                    return t && t.__esModule ? t : {
                        default: t
                    }
                }
                var p = /:/g,
                    m = {
                        local: {},
                        sta: {}
                    },
                    T = parseInt(Date.now() / 1e3),
                    S = function(t) {
                        var e = this;
                        this._statusData = t, _escObj(t), this._statusProperties = new n.default, this._proxies = new o.default.Collection, this._selectedStationProperties = new n.default, this._stationData = t.wireless.sta, _escObj(this._stationData), this._stationCollection = new l.default, this._interfaceCollection = new d.default, this._airCubeCollection = new u.default, this._reloadStatus(t), this._selectedStationMac = "", this._selectedStationIp = "", i.default.vent.on("rf_environment:station_selected", function(t) {
                            var a = e._stationCollection.findByMac(t);
                            a ? e._selectedStationProperties.set(a.get("properties").models) : e._selectedStationProperties.set([]), e._selectedStationMac = t, e._selectedStationIp = e._getStationIp(a.get("data")), i.default.vent.trigger("station_changed", t)
                        }), this._isDefaultPassword = !1, this._isWatchdogReset = 0, this._ubntboxLabel = "", this._previousStations = []
                    };
                S.prototype = {
                    _isAllStationsMSeries: !0,
                    _getValue: function(t) {
                        return {
                            value: t,
                            textValue: t
                        }
                    },
                    _getBooleanValue: function(t) {
                        return {
                            value: t,
                            textValue: t ? __("Enabled") : __("Disabled")
                        }
                    },
                    _parseStatusData: function(t) {
                        var e = [];
                        this.wlan = this._getInterface("ath0"), e.push(f.default.extend({
                            id: this.PLACEHOLDER,
                            label: ""
                        }, this._getValue(""))), e.push(f.default.extend({
                            id: this.PLACEHOLDER_B,
                            label: ""
                        }, this._getValue(""))), e.push(f.default.extend({
                            id: this.DEVICE_MODEL,
                            label: __("Device Model")
                        }, this._getValue(r.default.getValue(t, "host.devmodel", "")))), e.push(f.default.extend({
                            id: this.DEVICE_NAME,
                            label: __("Device Name")
                        }, this._getValue(r.default.getValue(t, "host.hostname", ""))));
                        var a = i.default.device.board.getFccId();
                        if (a && e.push(f.default.extend({
                                id: this.FCC_ID,
                                label: __("FCC ID")
                            }, this._getValue(a))), e.push(f.default.extend({
                                id: this.FIRMWARE,
                                label: __("Version")
                            }, this._getFirmwareVersion())), e.push(f.default.extend({
                                id: this.DATE,
                                label: __("Date")
                            }, this._getValue(this._getDate(!1)))), e.push(f.default.extend({
                                id: this.NETWORK_MODE,
                                label: __("Network Mode")
                            }, this._getNetworkMode(!1))), r.default.getValue(t, "custom_scripts", !1) && e.push({
                                id: this.CUSTOM_SCRIPTS_ENABLED,
                                label: __("Custom Scripts"),
                                value: !0,
                                textValue: __("Enabled")
                            }), e.push(f.default.extend({
                                id: this.MEMORY_USAGE,
                                label: __("Memory")
                            }, this._getMemoryUsage(!1))), e.push(f.default.extend({
                                id: this.CPU_USAGE,
                                label: __("CPU")
                            }, this._getCpuUsage(!1))), e.push(f.default.extend({
                                id: this.LAN_SPEED
                            }, this._getLanSpeed(!1))), e.push(f.default.extend({
                                id: this.CABLE_LENGTH,
                                label: __("Cable Length")
                            }, this._getCableLength(!1))), e.push(f.default.extend({
                                id: this.CABLE_SNR,
                                label: __("Cable SNR")
                            }, this._getAverageSnr(!1))), e.push(f.default.extend({
                                id: this.UPTIME,
                                label: __("Uptime")
                            }, this._getUptime(r.default.getValue(this._statusData, "host.uptime", 0)))), e.push(f.default.extend({
                                id: this.WIRELESS_MODE,
                                label: __("Wireless Mode")
                            }, this._getValue(this._getWirelessMode()))), e.push(f.default.extend({
                                id: this.WIRELESS_STATE,
                                label: __("Wireless State")
                            }, this._getWirelessState())), e.push(f.default.extend({
                                id: this.FREQUENCY_CENTER1,
                                label: __("Center1 Frequency")
                            }, this._getFrequencyCenter1())), e.push(f.default.extend({
                                id: this.GPS_TIME_SYNC_TIMESTAMP,
                                label: __("GPS Sync Timestamp")
                            }, this._getValue(r.default.getValue(this._statusData, "gps.last_sync", "")))), e.push(f.default.extend({
                                id: this.GPS_TIME_SYNC_ENABLED,
                                label: __("GPS Sync Enabled")
                            }, this._getBooleanValue(!!r.default.getValue(this._statusData, "gps.time_sync_enabled", !1)))), e.push(f.default.extend({
                                id: this.GPS_SIGNAL,
                                label: __("GPS Signal")
                            }, this._getGpsSignal())), e.push(f.default.extend({
                                id: this.GPS_LOCATION,
                                label: __("Location")
                            }, this._getGpsLocation())), e.push(f.default.extend({
                                id: this.GPS_ALTITUDE,
                                label: __("Altitude")
                            }, this._getGpsAltitude())), e.push(f.default.extend({
                                id: this.GPS_SAT_COUNT,
                                label: __("Satellites tracked")
                            }, this._getValue(r.default.getValue(this._statusData, "gps.sats", 0)))), e.push({
                                id: this.MCA_STATUS,
                                label: __(""),
                                value: this.isMcadReporting(),
                                textValue: this.isMcadReporting() ? "Reporting" : ""
                            }), e.push(f.default.extend({
                                id: this.PROVMODE_STATUS,
                                label: __("Provmode Status")
                            }, this._getValue(r.default.getValue(this._statusData, "provmode.status", -1)))), e.push(f.default.extend({
                                id: this.PROVMODE_TIMEOUT,
                                label: __("Provmode Timeout")
                            }, this._getValue(r.default.getValue(this._statusData, "provmode.timeout", 0)))), e.push(f.default.extend({
                                id: this.NTP_TIMESTAMP,
                                label: __("NTP Timestamp")
                            }, this._getValue(r.default.getValue(this._statusData, "ntpclient.last_sync", "")))), e.push(f.default.extend({
                                id: this.UNMS,
                                label: __("UNMS")
                            }, this._getUnmsInfo())), e.push(f.default.extend({
                                id: this.ANTENNA_GAIN,
                                label: __("Antenna Gain")
                            }, this._getValue(r.default.getValue(this._statusData, "host.antenna_gain", 0)))), this.isWlanEnabled()) {
                            if (this._getPollingEnabled() && (e.push({
                                    id: this.AIRMAX_ENABLED,
                                    label: "airMAX",
                                    value: !0,
                                    textValue: __("Enabled")
                                }), e.push(f.default.extend({
                                    id: this.AVERAGE_CAPACITY_TX_RX,
                                    label: __("Average Capacity TX/RX")
                                }, this._getAverageCapacity())), e.push(f.default.extend({
                                    id: this.ISOLATED_CAPACITY_TX_RX_PTP_AP,
                                    label: __("Isolated Capacity TX/RX")
                                }, this._getAverageCapacity())), e.push(f.default.extend({
                                    id: this.ISOLATED_CAPACITY_TX_RX,
                                    label: __("Isolated Capacity TX/RX")
                                }, this._getIsolatedCapacity())), e.push(f.default.extend({
                                    id: this.ISOLATED_CAPACITY_TX,
                                    label: __("TX Isolated Capacity")
                                }, this._getValue(this._getIsolatedCapacityTx()))), e.push(f.default.extend({
                                    id: this.ISOLATED_CAPACITY_RX,
                                    label: __("RX Isolated Capacity")
                                }, this._getValue(this._getIsolatedCapacityRx()))), e.push(f.default.extend({
                                    id: this.AIRTIME,
                                    label: __("Airtime")
                                }, this._getAirTime())), e.push(f.default.extend({
                                    id: this.TX_RX_AIRTIME,
                                    label: __("TX/RX Airtime")
                                }, this._getValue(this._getTxRxAirtime() + " %"))), e.push(f.default.extend({
                                    id: this.TDD_FRAMING,
                                    label: __("TDD Framing")
                                }, this._getTddFraming())), e.push(f.default.extend({
                                    id: this.TDD_FRAMING_GPS_SYNC,
                                    label: __("GPS Sync")
                                }, this._getValue(this.getTddFramingGpsSync()))), e.push(f.default.extend({
                                    id: this.TDD_FRAMING_DL_RATIO,
                                    label: __("DL/UL Ratio")
                                }, this._getTddFramingDlRatio()))), this._getDfsTime() > 0 && e.push(f.default.extend({
                                    id: this.DFS_WAIT_TIME,
                                    label: __("DFS Wait")
                                }, this._getValue(this._getDfsTime() + " s"))), e.push(f.default.extend({
                                    id: this.TX_BYTES,
                                    label: __("TX Bytes")
                                }, this._getValue(this._getTxBytes()))), e.push(f.default.extend({
                                    id: this.RX_BYTES,
                                    label: __("RX Bytes")
                                }, this._getValue(this._getRxBytes()))), e.push(f.default.extend({
                                    id: this.SSID
                                }, this._getSSID())), e.push(f.default.extend({
                                    id: this.WLAN_MAC
                                }, this._getWlanMac())), this.isSta() && e.push(f.default.extend({
                                    id: this.AP_MAC,
                                    label: __("AP MAC")
                                }, this._getApMac())), e.push(f.default.extend({
                                    id: this.SIGNAL,
                                    label: __("RX Signal")
                                }, this._getSignal())), e.push({
                                    id: this.CONNECTIONS,
                                    label: __("Connections"),
                                    value: r.default.getValue(t, "wireless.sta", []).length,
                                    textValue: r.default.getValue(t, "wireless.sta", []).length || "-"
                                }), e.push(f.default.extend({
                                    id: this.FREQUENCY,
                                    label: __("Frequency")
                                }, this._getFrequency())), e.push(f.default.extend({
                                    id: this.CHANNEL_WIDTH,
                                    label: __("Channel Width")
                                }, this._getChannelWidth())), e.push(f.default.extend({
                                    id: this.NOISE_FLOOR,
                                    label: __("Noise Floor")
                                }, this._getValue(this._getNoiseFloor()))), this._getWirelessState().value === this.WirelessState.CONNECTED) {
                                e.push(f.default.extend({
                                    id: this.STATION_REMOTE_NOISE_FLOOR,
                                    label: __("Noise Floor")
                                }, this._getValue(this._getRemoteNoiseFloor()))), e.push(f.default.extend({
                                    id: this.TX_RATE,
                                    label: __("TX Rate")
                                }, this._getValue(this._getTxRate()))), e.push(f.default.extend({
                                    id: this.RX_RATE,
                                    label: __("RX Rate")
                                }, this._getValue(this._getRxRate()))), e.push(f.default.extend({
                                    id: this.SIGNAL_PER_CHAIN_REMOTE,
                                    label: __("RX") + " " + this.getChainNames()
                                }, this.getStationRemoteChainSignal())), e.push(f.default.extend({
                                    id: this.TX_POWER,
                                    label: __("TX Power")
                                }, this._getTxPower(!1))), e.push(f.default.extend({
                                    id: this.TX_RX_BYTES,
                                    label: __("TX/RX Bytes")
                                }, this._getValue(this._getTxRxBytes()))), e.push(f.default.extend({
                                    id: this.DISTANCE,
                                    label: __("Distance")
                                }, this._getDistance())), e.push(f.default.extend({
                                    id: this.DISTANCE_FROM_COORDINATES,
                                    label: __("Distance")
                                }, this._getDistanceFromCoordinates()));
                                var s = this.getDownlinkCapacity();
                                e.push({
                                    id: this.DOWNLINK_CAPACITY,
                                    label: __("Downlink Capacity"),
                                    value: s > 0 ? r.default.formatBPS(s)[3] : "-",
                                    textValue: s > 0 ? r.default.formatBPS(s)[3] : "-",
                                    rawValue: s
                                });
                                s = this.getUplinkCapacity();
                                e.push({
                                    id: this.UPLINK_CAPACITY,
                                    label: __("Uplink Capacity"),
                                    value: s > 0 ? r.default.formatBPS(s)[3] : "-",
                                    textValue: s > 0 ? r.default.formatBPS(s)[3] : "-",
                                    rawValue: s
                                }), e.push(f.default.extend({
                                    id: this.SECURITY,
                                    label: __("Security")
                                }, this._getValue(this._getSecurity()))), e.push({
                                    id: this.PLACEHOLDER_CONNECTED,
                                    label: " ",
                                    value: ""
                                })
                            } else e.push({
                                id: this.NOT_CONNECTED,
                                label: __("Not Connected"),
                                value: ""
                            }), e.push({
                                id: this.PLACEHOLDER_DISCONNECTED_1,
                                label: " ",
                                value: ""
                            }), e.push({
                                id: this.PLACEHOLDER_DISCONNECTED_2,
                                label: " ",
                                value: ""
                            }), e.push({
                                id: this.PLACEHOLDER_DISCONNECTED_3,
                                label: " ",
                                value: ""
                            }), e.push({
                                id: this.PLACEHOLDER_DISCONNECTED_4,
                                label: " ",
                                value: ""
                            }), e.push({
                                id: this.CONNECTIONS,
                                label: __("Connections"),
                                value: 0,
                                textValue: "-"
                            });
                            this._getAntennaCount() > 1 && e.push(f.default.extend({
                                id: this.ANTENNA,
                                label: __("Antenna")
                            }, this._getValue(r.default.getValue(t, "wireless.antenna", ""))))
                        } else e.push({
                            id: this.WLAN_DISABLED,
                            label: __("Wireless Disabled"),
                            value: ""
                        }), e.push({
                            id: this.CONNECTIONS,
                            label: __("Connections"),
                            value: 0,
                            textValue: "-"
                        });
                        this._statusProperties.set(e)
                    },
                    _reloadStatus: function(e) {
                        var a, n = this,
                            l = 0,
                            u = function() {
                                clearTimeout(a), a = setTimeout(o, s.default.getDeviceStatusReloadInterval())
                            },
                            o = function() {
                                i.default.areHeartbeatsEnabled() ? t.ajax({
                                    url: s.default.getStatusUrl(),
                                    cache: !1,
                                    dataType: "json",
                                    timeout: 2e3
                                }).done(function(t, e, a) {
                                    if (204 == a.status && l++, "success" == e) {
                                        _escObj(t), window.sa && function(t) {
                                            function e(t, e) {
                                                return Math.floor(Math.random() * (e - t + 1)) + t
                                            }

                                            function a(t, a) {
                                                return e(1e3 * t, 1e3 * a)
                                            }

                                            function i(t, a) {
                                                return e(1e3 * t * 100, 1e3 * a * 100)
                                            }
                                            t.host.uptime = parseInt(Date.now() / 1e3) - T + 6e3, t.host.timestamp = Date.now(), m.local.txBytes ? (m.local.txBytes += i(95, 120), m.local.rxBytes += i(75, 90), e(0, 10) % 10 == 0 && (m.local.downlink_capacity = a(230, 250)), e(0, 10) % 10 == 0 && (m.local.uplink_capacity = a(200, 230))) : m.local = {
                                                txBytes: i(95, 120),
                                                rxBytes: i(75, 90),
                                                downlink_capacity: a(230, 250),
                                                uplink_capacity: a(200, 230)
                                            }, t.wireless.polling.dcap = m.local.downlink_capacity, t.wireless.polling.ucap = m.local.uplink_capacity, t.interfaces[1].status.tx_bytes = m.local.txBytes, t.interfaces[1].status.rx_bytes = m.local.rxBytes, f.default.each(t.wireless.sta, function(t) {
                                                m.sta[t.mac] ? (m.sta[t.mac].txBytes += i(30, 45), m.sta[t.mac].rxBytes += i(40, 65), e(0, 10) % 10 == 0 && (m.sta[t.mac].downlink_capacity = a(230, 250)), e(0, 10) % 10 == 0 && (m.sta[t.mac].uplink_capacity = a(200, 230))) : m.sta[t.mac] = {
                                                    txBytes: i(30, 45),
                                                    rxBytes: i(35, 50),
                                                    downlink_capacity: a(230, 250),
                                                    uplink_capacity: a(200, 230)
                                                }, t.stats.rx_bytes = m.sta[t.mac].rxBytes, t.stats.tx_bytes = m.sta[t.mac].txBytes, t.airmax.downlink_capacity = m.sta[t.mac].downlink_capacity, t.airmax.uplink_capacity = m.sta[t.mac].uplink_capacity
                                            })
                                        }(t), n._statusData = t, n._parseStatusData(t), l > 0 && (i.default.vent.trigger("heartbeat:on_again", l), l = 0), i.default.vent.trigger("status:updated", n._statusData);
                                        var u = [];
                                        if (f.default.isDefined(n._statusData.interfaces)) {
                                            for (var o = 0; o < n._statusData.interfaces.length; o++) {
                                                var _ = n._statusData.interfaces[o];
                                                _.id = _.ifname.replace(/\./g, "_"), _.name = r.default.devname2uidevname(_.ifname), u.push(_)
                                            }
                                            n._interfaceCollection.set(u)
                                        }
                                        i.default.vent.trigger("status:interface_list_updated", n._stationData), n._stationData = n._statusData.wireless.sta, n._parseStationData(n._stationData), i.default.vent.trigger("status:station_list_updated", n._stationData)
                                    } else l >= s.default.getFailureCountBeforeBlock() && (window.location.href = s.default.getIndexUrl())
                                }).fail(function(t, e, a) {
                                    l++, i.default.vent.trigger("heartbeat:failed", l), c.default.error("Device status reload failed")
                                }).always(function() {
                                    u()
                                }) : u()
                            };
                        e ? (this._parseStatusData(e), n._stationData = n._statusData.wireless.sta, n._parseStationData(n._stationData), i.default.vent.trigger("status:station_list_updated", n._stationData), u()) : o()
                    },
                    _getStationIp: function(t) {
                        var e = r.default.getValue(t, "lastip", "");
                        if (!e || "0.0.0.0" === e) {
                            var a = r.default.getValue(t, "remote.ipaddr", []);
                            a.length && (e = a[0])
                        }
                        return e
                    },
                    _parseStationData: function(t) {
                        var e = [],
                            a = [],
                            s = [],
                            l = "",
                            u = "";
                        this._isAllStationsMSeries = !0;
                        for (var o = 0; o < t.length; o++) {
                            this._remoteEndData = t[o];
                            var _ = r.default.getValue(this._remoteEndData, "mac", ""),
                                d = this._getStationIp(this._remoteEndData);
                            a.push(_), "" == this._selectedStationMac && (this._selectedStationMac = _, i.default.vent.trigger("station_changed", _)), "" == this._selectedStationIp && (this._selectedStationIp = d);
                            var c = [];
                            if (c.push(f.default.extend({
                                    id: this.STATION_SIGNAL_TX_RX,
                                    label: __("Signal TX/RX")
                                }, this._getValue(this._getStationSignalTxRx()))), c.push({
                                    id: this.STATION_SIGNAL_TX,
                                    label: __("Signal TX"),
                                    value: parseInt(r.default.getValue(this._remoteEndData, "remote.signal", 0)),
                                    textValue: r.default.getValue(this._remoteEndData, "remote.signal", 0) + " dBm"
                                }), c.push({
                                    id: this.STATION_SIGNAL_RX,
                                    label: __("Signal RX"),
                                    value: parseInt(r.default.getValue(this._remoteEndData, "signal", 0)),
                                    textValue: r.default.getValue(this._remoteEndData, "signal", 0) + " dBm"
                                }), c.push(f.default.extend({
                                    id: this.STATION_REMOTE_SIGNAL,
                                    label: __("RX Signal")
                                }, this._getStationRemoteSignal())), c.push(f.default.extend({
                                    id: this.STATION_REMOTE_SIGNAL_AP,
                                    label: __("RX Signal")
                                }, this._getStationRemoteSignal())), c.push(f.default.extend({
                                    id: this.STATION_SIGNAL,
                                    label: __("RX Signal")
                                }, this._getStationSignal())), c.push(f.default.extend({
                                    id: this.STATION_REMOTE_SIGNAL_PER_CHAIN,
                                    label: __("RX") + " " + this.getChainNames()
                                }, this.getStationRemoteChainSignal())), c.push(f.default.extend({
                                    id: this.STATION_SIGNAL_PER_CHAIN,
                                    label: __("RX") + " " + this.getChainNames()
                                }, this._getValue(this._getChainSignal()))), this.getStationActiveChainCount() > 0) {
                                c.push(f.default.extend({
                                    id: this.STATION_SIGNAL_PER_CHAIN0,
                                    label: __("RX") + " " + this.getChainNames()
                                }, this._getValue(this._getChainSignal(0)))), c.push(f.default.extend({
                                    id: this.STATION_SIGNAL_PER_CHAIN1,
                                    label: __("RX") + " " + this.getChainNames()
                                }, this._getValue(this._getChainSignal(1))));
                                var h = this.getStationActiveChainCount(),
                                    g = this.getStationRemoteActiveChainCount(_);
                                c.push(f.default.extend({
                                    id: this.STATION_SIGNAL_CHAIN_DIFF_TOO_HIGH,
                                    label: __("RX Chain 0 and RX Chain 1 difference too high")
                                }, this._getValue(this._isChainSignalDiffTooHigh(this._getChainSignal(0), this._getChainSignal(1), h)))), c.push(f.default.extend({
                                    id: this.STATION_REMOTE_SIGNAL_CHAIN_DIFF_TOO_HIGH,
                                    label: __("RX Chain 0 and RX Chain 1 difference too high")
                                }, this._getValue(this._isChainSignalDiffTooHigh(this._getChainSignal(0, !0), this._getChainSignal(1, !0), g)))), c.push(f.default.extend({
                                    id: this.STATION_SIGNAL_CHAIN_DIFF,
                                    label: __("RX Chain 0 and RX Chain 1 imbalance")
                                }, this._getValue(this._getChainImbalance(this._getChainSignal(0), this._getChainSignal(1), h)))), c.push(f.default.extend({
                                    id: this.STATION_REMOTE_SIGNAL_CHAIN_DIFF,
                                    label: __("RX Chain 0 and RX Chain 1 imbalance")
                                }, this._getValue(this._getChainImbalance(this._getChainSignal(0, !0), this._getChainSignal(1, !0), g))))
                            }
                            c.push(f.default.extend({
                                id: this.STATION_REMOTE_TX_POWER,
                                label: __("TX Power")
                            }, this._getTxPower(!0))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_TX_POWER_B,
                                label: __("Remote TX Power")
                            }, this._getValue(r.default.getValue(this._remoteEndData, "remote.tx_power", "-") + " dBm"))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_DEVICE_MODEL,
                                label: __("Device Model")
                            }, this._getValue(r.default.getValue(this._remoteEndData, "remote.platform", "")))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_DEVICE_NAME,
                                label: __("Device Name")
                            }, this._getValue(r.default.getValue(this._remoteEndData, "remote.hostname", "")))), c.push({
                                id: this.STATION_MAC,
                                label: __("MAC Address"),
                                value: _,
                                textValue: _
                            }), c.push({
                                id: this.STATION_MAC_B,
                                label: __("STA MAC"),
                                value: _,
                                textValue: _
                            }), c.push(f.default.extend({
                                id: this.STATION_REMOTE_FIRMWARE,
                                label: __("Version"),
                                sValue: {
                                    label: this._getStationRemoteFirmware()
                                }
                            }, this._getValue(this._getStationRemoteFirmware()))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_VERSION_FULL,
                                label: __("Version")
                            }, this._getValue(this._getStationRemoteFirmware(!0)))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_WIRELESS_MODE,
                                label: __("Wireless Mode")
                            }, this._getValue(this._getWirelessMode(!0)))), c.push(f.default.extend({
                                id: this.STATION_CONNECTION_TIME,
                                label: __("Connection Time")
                            }, this._getUptime(r.default.getValue(this._remoteEndData, "uptime", 0)))), c.push(f.default.extend({
                                id: this.STATION_LAST_IP,
                                label: __("Last IP")
                            }, this._getValue(d))), c.push(f.default.extend({
                                id: this.STATION_NOISE_FLOOR,
                                label: __("Noise Floor")
                            }, this._getValue(this._getStationNoiseFloor()))), c.push(f.default.extend({
                                id: this.STATION_LATENCY,
                                label: __("Latency")
                            }, this._getValue(r.default.getValue(this._remoteEndData, "tx_latency", "-") + " ms"))), c.push(f.default.extend({
                                id: this.STATION_AIRTIME,
                                label: __("Airtime TX/RX")
                            }, this._getValue(this._getStationAirtime()))), c.push(f.default.extend({
                                id: this.STATION_AIRTIME_TX,
                                label: __("Airtime TX")
                            }, this._getValue(this._getStationAirtimeTx()))), c.push(f.default.extend({
                                id: this.STATION_AIRTIME_RX,
                                label: __("Airtime RX")
                            }, this._getValue(this._getStationAirtimeRx()))), c.push(f.default.extend({
                                id: this.STATION_TX_RX_AIRTIME,
                                label: __("TX/RX Airtime")
                            }, this._getValue(this._getStationAirtime() + " %")));
                            var m = this._getStationDownlinkCapacity();
                            c.push({
                                id: this.STATION_DOWNLINK_CAPACITY,
                                label: __("Downlink Capacity"),
                                value: m > 0 ? r.default.formatBPS(m)[3] : "-",
                                textValue: m > 0 ? r.default.formatBPS(m)[3] : "-",
                                rawValue: m
                            });
                            m = this._getStationUplinkCapacity();
                            c.push({
                                id: this.STATION_UPLINK_CAPACITY,
                                label: __("Uplink Capacity"),
                                value: m > 0 ? r.default.formatBPS(m)[3] : "-",
                                textValue: m > 0 ? r.default.formatBPS(m)[3] : "-",
                                rawValue: m
                            }), c.push(f.default.extend({
                                id: this.STATION_BEAM,
                                label: __("Beam")
                            }, this._getValue(r.default.getValue(this._remoteEndData, "airmax.beam", 0)))), c.push(f.default.extend({
                                id: this.STATION_PPS,
                                label: __("TX/RX PPS")
                            }, this._getValue(this._getStationPps()))), c.push(f.default.extend({
                                id: this.STATION_DISTANCE,
                                label: __("Distance")
                            }, this._getStationDistance())), c.push(f.default.extend({
                                id: this.STATION_REMOTE_DISTANCE,
                                label: __("Distance")
                            }, this._getStationRemoteDistance())), c.push(f.default.extend({
                                id: this.STATION_TX_RATE,
                                label: __("TX Rate")
                            }, this._getStationTxRate())), c.push(f.default.extend({
                                id: this.STATION_RX_RATE,
                                label: __("RX Rate")
                            }, this._getStationRxRate())), c.push(f.default.extend({
                                id: this.STATION_TX_RX_BYTES,
                                label: __("TX/RX Bytes")
                            }, this._getValue(this._getStationTxRxBytes(!1)))), c.push(f.default.extend({
                                id: this.STATION_TX_BYTES,
                                label: __("TX Bytes")
                            }, this._getValue(this._getStationTxBytes()))), c.push(f.default.extend({
                                id: this.STATION_RX_BYTES,
                                label: __("RX Bytes")
                            }, this._getValue(this._getStationRxBytes()))), c.push(f.default.extend({
                                id: this.STATION_ISOLATED_CAPACITY_TX_RX,
                                label: __("Isolated Capacity TX/RX")
                            }, this._getValue(this._getStationIsolatedCapacity()))), c.push(f.default.extend({
                                id: this.STATION_AVERAGE_CAPACITY_TX_RX,
                                label: __("Average Capacity TX/RX")
                            }, this._getValue(this._getStationAverageCapacity()))), c.push(f.default.extend({
                                id: this.STATION_ISOLATED_CAPACITY_TX_RX_PTP,
                                label: __("Isolated Capacity TX/RX")
                            }, this._getValue(this._getStationAverageCapacity()))), c.push(f.default.extend({
                                id: this.STATION_ACTUAL_PRIORITY,
                                label: __("Priority")
                            }, this._getValue(this._getActualPriority()))), c.push(f.default.extend({
                                id: this.STATION_DESIRED_PRIORITY,
                                label: __("Desired Priority")
                            }, this._getValue(this._getDesiredPriority()))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_DATE,
                                label: __("Date")
                            }, this._getValue(this._getDate(!0)))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_NETWORK_MODE,
                                label: __("Network Mode")
                            }, this._getNetworkMode(!0))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_UPTIME,
                                label: __("Uptime")
                            }, this._getUptime(r.default.getValue(this._remoteEndData, "remote.uptime", 0)))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_MEMORY_USAGE,
                                label: __("Memory")
                            }, this._getMemoryUsage(!0))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_CPU_USAGE,
                                label: __("CPU")
                            }, this._getCpuUsage(!0))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_LAN_SPEED,
                                label: __("Lan Speed")
                            }, this._getLanSpeed(!0))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_CABLE_LENGTH,
                                label: __("Cable Length")
                            }, this._getCableLength(!0))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_CABLE_SNR,
                                label: __("Cable SNR")
                            }, this._getAverageSnr(!0))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_TX_RX_BYTES,
                                label: __("TX/RX Bytes")
                            }, this._getValue(this._getStationTxRxBytes(!0)))), c.push(f.default.extend({
                                id: this.SNR_LOCAL_CINR,
                                label: __("CINR")
                            }, this._getValue(3 == r.default.getValue(this._remoteEndData, "airmax.rx.cinr", 3) ? "-" : "+" + r.default.getValue(this._remoteEndData, "airmax.rx.cinr", 3) + " dB"))), c.push(f.default.extend({
                                id: this.SNR_REMOTE_CINR,
                                label: __("CINR")
                            }, this._getValue(3 == r.default.getValue(this._remoteEndData, "airmax.tx.cinr", 3) ? "-" : "+" + r.default.getValue(this._remoteEndData, "airmax.tx.cinr", 3) + " dB"))), c.push(f.default.extend({
                                id: this.SIGNAL_PER_CHAIN,
                                label: __("RX") + " " + this.getChainNames()
                            }, this._getSignalPerChain())), c.push(f.default.extend({
                                id: this.STATION_REMOTE_GPS_SIGNAL,
                                label: __("GPS Signal")
                            }, this._getGpsSignal(!0))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_GPS_LOCATION,
                                label: __("Location")
                            }, this._getGpsLocation(!0))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_GPS_ALTITUDE,
                                label: __("Altitude")
                            }, this._getGpsAltitude(!0))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_GPS_SAT_COUNT,
                                label: __("Satellites tracked")
                            }, this._getValue(r.default.getValue(this._remoteEndData, "remote.gps.sats", 0)))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_ANTENNA_GAIN,
                                label: __("Antenna Gain")
                            }, this._getValue(r.default.getValue(this._remoteEndData, "remote.antenna_gain", 0)))), c.push(f.default.extend({
                                id: this.STATION_REMOTE_TDD_FRAMING_DL_RATIO,
                                label: __("DL/UL Ratio")
                            }, this._getTddFramingDlRatio())), c.push(f.default.extend({
                                id: this.STATION_REMOTE_UNMS,
                                label: __("UNMS")
                            }, this._getUnmsInfo(!0)));
                            var T = this._stationCollection.findByMac(_);
                            if (T) T.get("properties").set(c), T.set("data", t[o]);
                            else this._stationCollection.add({
                                id: _.replace(p, ""),
                                mac: _,
                                properties: new n.default(c),
                                data: t[o]
                            }), T = this._stationCollection.findByMac(_);
                            T.get("mac") == this._selectedStationMac && (e = c), "" == l && (l = _, u = d, s = c);
                            var S = this.getStationPropertyValue(_, this.STATION_REMOTE_VERSION_FULL);
                            this._isAllStationsMSeries && !this._isMSeries(S) && (this._isAllStationsMSeries = !1)
                        }
                        var v = f.default.reject(this._stationCollection.models, function(t) {
                            return -1 == f.default.indexOf(a, t.get("mac"))
                        });
                        this._stationCollection.set(v), 0 == e.length ? (this._selectedStationMac = l, this._selectedStationIp = u, this._selectedStationProperties.set(s)) : this._selectedStationProperties.set(e);
                        var A = f.default.difference(this._previousStations, a),
                            E = f.default.difference(a, this._previousStations);
                        (A.length > 0 || E.length > 0) && i.default.vent.trigger("status:station_list:changed", E, A, this._previousStations), this._previousStations = a
                    },
                    getPropertyCollectionSubset: function(t, e) {
                        var a = this._proxies.findWhere({
                            id: t
                        });
                        if (a) return a.get("collection");
                        var i = new n.default;
                        i.comparator = t + "_position";
                        for (var s = 0; s < e.length; s++) {
                            var l = this._statusProperties.findWhere({
                                id: e[s]
                            });
                            f.default.isUndefined(l) && (l = this._selectedStationProperties.findWhere({
                                id: e[s]
                            })), l && (l.set(i.comparator, s), i.add(l))
                        }
                        var u = function(t) {
                            var a = f.default.indexOf(e, t.id); - 1 != a && (t.set(i.comparator, a), i.add(t))
                        };
                        i.listenTo(this._statusProperties, "add", function(t) {
                            u(t)
                        }), i.listenTo(this._selectedStationProperties, "add", function(t) {
                            u(t)
                        });
                        var o = function(t) {
                            -1 != f.default.indexOf(e, t.id) && i.remove(t)
                        };
                        return i.listenTo(this._statusProperties, "remove", function(t) {
                            o(t)
                        }), i.listenTo(this._selectedStationProperties, "remove", function(t) {
                            o(t)
                        }), this._proxies.add({
                            id: t,
                            collection: i
                        }), i
                    },
                    getProperty: function(t) {
                        var e = this._statusProperties.findWhere({
                            id: t
                        });
                        return f.default.isUndefined(e) && (e = this._selectedStationProperties.findWhere({
                            id: t
                        })), e
                    },
                    getStationProperty: function(t, e) {
                        var a = this._stationCollection.findByMac(t);
                        return a ? a.get("properties").findWhere({
                            id: e
                        }) : null
                    },
                    getStationPropertyValue: function(t, e, a) {
                        var i = this.getStationProperty(t, e);
                        return i ? i.get(f.default.isUndefined(a) ? "value" : "textValue") : null
                    },
                    getStationDataByMac: function(t) {
                        var e = this._stationCollection.findByMac(t);
                        return e ? e.get("data") : null
                    },
                    getValue: function(t) {
                        var e = this.getProperty(t);
                        return e ? e.get("value") : null
                    },
                    _getFirmwareVersion: function() {
                        var t = r.default.getValue(this._statusData, "host.fwversion", ""),
                            e = this.getFirmwarePrefix();
                        return {
                            value: r.default.stripFirmwareVersion(t) + (e ? " (" + e + ")" : ""),
                            textValue: r.default.stripFirmwareVersion(t) + (e ? "( " + e + ")" : "")
                        }
                    },
                    getNetworkMode: function() {
                        return r.default.getValue(this._statusData, "host.netrole", "")
                    },
                    isBridge: function() {
                        return "bridge" === this.getNetworkMode()
                    },
                    isRouter: function() {
                        return "router" === this.getNetworkMode()
                    },
                    _getNetworkMode: function(t) {
                        if (t) var e = r.default.getValue(this._remoteEndData, "remote.netrole", "");
                        else e = r.default.getValue(this._statusData, "host.netrole", "");
                        var a;
                        switch ("unknown" !== e && "" !== e || (a = "-"), e) {
                            case "bridge":
                                a = __("Bridge");
                                break;
                            case "router":
                                a = __("Router");
                                break;
                            case "soho":
                                a = __("SOHO Router");
                                break;
                            case "3g":
                                a = __("3G Router")
                        }
                        return {
                            value: a,
                            textValue: a
                        }
                    },
                    _getMemoryUsage: function(t) {
                        if (t) var e = r.default.getValue(this._remoteEndData, "remote.totalram", 1),
                            a = r.default.getValue(this._remoteEndData, "remote.freeram", 1);
                        else e = r.default.getValue(this._statusData, "host.totalram", 1), a = r.default.getValue(this._statusData, "host.freeram", 1);
                        if (0 == e && 0 == a) var i = "-";
                        else i = r.default.getPercentage(e - a, e);
                        return {
                            value: i,
                            textValue: i + "%"
                        }
                    },
                    _getCpuUsage: function(t) {
                        if (t) var e = Math.round(r.default.getValue(this._remoteEndData, "remote.cpuload", 0));
                        else e = Math.round(r.default.getValue(this._statusData, "host.cpuload", 0));
                        return {
                            value: e,
                            textValue: e + "%"
                        }
                    },
                    _getCableLength: function(t) {
                        var e;
                        e = t ? r.default.getValue(this._remoteEndData, "remote.ethlist", []) : this._getLanInterfaces();
                        for (var a = [], i = 0; i < e.length; i++) {
                            var n = e[i].status ? e[i].status.cable_len : e[i].cable_len;
                            (e[i].status ? e[i].status.plugged : e[i].plugged) || (n = -1), void 0 === n && (n = -1), s.default.usesImperialUnits() ? a.push(-1 != n ? n < 20 ? "&lt; 65 ft" : Math.round(r.default.metersToFeet(n)) + " ft" : "-") : a.push(-1 != n ? n < 20 ? "&lt; 20 m" : n + " m" : "-")
                        }
                        var l = a.join(" / ");
                        return {
                            value: l,
                            textValue: l
                        }
                    },
                    getCableLength: function(t) {
                        var e = this._getInterface(t),
                            a = r.default.getValue(e.status, "cable_len", 0),
                            i = a;
                        return parseInt(a) < 20 && (i = "&lt; 20"), i
                    },
                    getIfcStatusVal: function(t, e) {
                        var a = this._getInterface(t);
                        return r.default.getValue(a.status, e, 0)
                    },
                    _getInterface: function(e) {
                        var a = t.grep(this._statusData.interfaces, function(t) {
                            return t.ifname == e
                        });
                        return a.length > 0 ? a[0] : null
                    },
                    _getLanInterfaces: function() {
                        var e = /eth[0-9]$/;
                        return t.grep(this._statusData.interfaces, function(t) {
                            return e.test(t.ifname)
                        })
                    },
                    getCableSnr: function(t, e) {
                        var a = e || r.default.getValue(this._getInterface(t).status, "snr", []);
                        if (4 == a.length) {
                            for (var i = 0; i < a.length; i++) a[i] = parseInt(a[i]);
                            return a
                        }
                        return [0, 0, 0, 0]
                    },
                    _getSingleAverageSnr: function(t, e) {
                        for (var a = this.getCableSnr(t, e), i = 0, s = 0, n = 0; n < a.length; n++) a[n] > 0 && (i += a[n], s++);
                        var l = 0;
                        s > 0 && (l = i / s);
                        var u = Math.round(l);
                        return {
                            value: 0 === u ? "-" : "+" + u + " " + __("dB"),
                            textValue: 0 === u ? "-" : "+" + u + " " + __("dB")
                        }
                    },
                    _getAverageSnr: function(t) {
                        var e, a, i = [];
                        e = t ? r.default.getValue(this._remoteEndData, "remote.ethlist", []) : this._getLanInterfaces();
                        for (var s = 0; s < e.length; s++) {
                            var n = e[s].status ? e[s].status.snr : e[s].snr;
                            i.push(this._getSingleAverageSnr(e[s].ifname, n).value)
                        }
                        return {
                            value: a = i.join(" / "),
                            textValue: a
                        }
                    },
                    isAirMaxEnabled: function() {
                        return this._getPollingEnabled()
                    },
                    _getPollingEnabled: function() {
                        return r.default.getValue(this._statusData, "wireless.polling.enabled", 1)
                    },
                    _getLanSpeed: function(t) {
                        var e;
                        e = t ? r.default.getValue(this._remoteEndData, "remote.ethlist", []) : this._getLanInterfaces();
                        var a = r.default.format_eth_str(e);
                        return {
                            label: a.label,
                            value: a.value,
                            textValue: a.value
                        }
                    },
                    calculateIsolatedCapacity: function(t, e) {
                        return (e > 0 ? r.default.formatBPS(1e3 * e)[3] : "-") + " / " + (t > 0 ? r.default.formatBPS(1e3 * t)[3] : "-")
                    },
                    _getIsolatedCapacity: function() {
                        var t = r.default.getValue(this._statusData, "wireless.polling.dcap", 0),
                            e = r.default.getValue(this._statusData, "wireless.polling.ucap", 0),
                            a = this.calculateIsolatedCapacity(t, e);
                        return {
                            value: a,
                            textValue: a
                        }
                    },
                    _getAverageCapacity: function() {
                        var t = r.default.getValue(this._statusData, "wireless.polling.dcap", 0),
                            e = r.default.getValue(this._statusData, "wireless.polling.ucap", 0),
                            a = this.calculateIsolatedCapacity(e, t);
                        return {
                            value: a,
                            textValue: a
                        }
                    },
                    _getIsolatedCapacityTx: function() {
                        var t = r.default.getValue(this._statusData, "wireless.polling.dcap", 0);
                        return t > 0 ? r.default.formatBPS(1e3 * t)[3] : "-"
                    },
                    _getIsolatedCapacityRx: function() {
                        var t = r.default.getValue(this._statusData, "wireless.polling.ucap", 0);
                        return t > 0 ? r.default.formatBPS(1e3 * t)[3] : "-"
                    },
                    _getStationUplinkCapacity: function() {
                        return 1e3 * r.default.getValue(this._remoteEndData, "airmax.uplink_capacity", 0)
                    },
                    getStationUplinkCapacity: function() {
                        var t = this.getStationProperty(this.getSelectedStationMac(), this.STATION_UPLINK_CAPACITY);
                        return t ? t.get("rawValue") : 0
                    },
                    _getStationDownlinkCapacity: function() {
                        return 1e3 * r.default.getValue(this._remoteEndData, "airmax.downlink_capacity", 0)
                    },
                    getStationDownlinkCapacity: function() {
                        var t = this.getStationProperty(this.getSelectedStationMac(), this.STATION_DOWNLINK_CAPACITY);
                        return t ? t.get("rawValue") : 0
                    },
                    getUplinkCapacity: function() {
                        return 1e3 * r.default.getValue(this._statusData, "wireless.polling.ucap", 0)
                    },
                    getDownlinkCapacity: function() {
                        return 1e3 * r.default.getValue(this._statusData, "wireless.polling.dcap", 0)
                    },
                    _getStationIsolatedCapacity: function() {
                        var t = r.default.getValue(this._remoteEndData, "airmax.downlink_capacity", 0),
                            e = r.default.getValue(this._remoteEndData, "airmax.uplink_capacity", 0);
                        return this.calculateIsolatedCapacity(t, e)
                    },
                    _getStationPps: function() {
                        var t = null,
                            e = "- / -";
                        if (i.default.chartController && (t = i.default.chartController.staCollection.findWhere({
                                id: r.default.getValue(this._remoteEndData, "mac", 0)
                            })), t) {
                            var a = t.get("data").getData().ppsRxData.values,
                                s = t.get("data").getData().ppsTxData.values;
                            e = s[s.length - 1] + " / " + a[a.length - 1]
                        }
                        return e
                    },
                    _getStationDistance: function() {
                        return this._formatDistance(r.default.getValue(this._remoteEndData, "distance", 0))
                    },
                    _getStationRemoteDistance: function() {
                        return this._formatDistance(r.default.getValue(this._remoteEndData, "remote.distance", 0))
                    },
                    _isDistanceLimitReached: function(t) {
                        return this.isPtmp() && i.default.device.wireless.checkDistanceWarning(t, this.getChanbw(), this.isFixedFrame() || this.isFlexibleFrameBeta())
                    },
                    _formatDistance: function(t) {
                        var e, a = !0,
                            s = t < i.default.settings.MIN_DISTANCE ? i.default.settings.MIN_DISTANCE : t,
                            n = this._isDistanceLimitReached(s);
                        if (n && (e = '<span data-file="distancewarning.html" class="help" style="color: red">' + e + ' <span class="icon ubnt-icon--alert"></span></span> '), 1e5 === s) n = !1, a = !1, e = __("measuring");
                        else {
                            var l = _.default.convert(s, "m", "km"),
                                u = _.default.convert(s, "m", "mi");
                            e = r.default.toFixed(u, 1) + " miles (" + r.default.toFixed(l, 1) + " km)"
                        }
                        return {
                            value: s,
                            textValue: e,
                            isLimitReached: n,
                            isDistanceCalculated: a,
                            title: __("Propagation-based distance")
                        }
                    },
                    _getDistanceFromCoordinates: function() {
                        var t = !1,
                            e = !1,
                            a = 0,
                            i = this.getGpsInfo(),
                            s = this.getGpsInfo(!0);
                        return i.hasCoordinates && s.hasCoordinates && (a = r.default.calculateDistanceFromCoordinates(i, s), t = this._isDistanceLimitReached(a), e = !0), {
                            isCalculated: e,
                            value: a,
                            isLimitReached: t,
                            title: __("Coordinate-based distance")
                        }
                    },
                    _formatRate: function(t, e) {
                        var a = i.default.device.wireless.formatRate(t, e),
                            s = i.default.device.wireless.calculateModulationRate(t, e);
                        return {
                            value: a,
                            textValue: a,
                            vhtRateIdx: t,
                            rateIdx: s ? s.modIdx : null,
                            rateX: s ? s.rateX : null,
                            modulation: s ? s.modulation : null,
                            codingRate: s ? s.codingRate : null,
                            io: s ? s.io : null
                        }
                    },
                    _getStationTxRate: function() {
                        return this._formatRate(r.default.getValue(this._remoteEndData, "tx_idx", 0), r.default.getValue(this._remoteEndData, "tx_nss", 0))
                    },
                    _getStationRxRate: function() {
                        return this._formatRate(r.default.getValue(this._remoteEndData, "rx_idx", 0), r.default.getValue(this._remoteEndData, "rx_nss", 0))
                    },
                    _getStationTxRxBytes: function(t) {
                        return r.default.formatBytesIf(this._getStationTxBytes(t)) + " / " + r.default.formatBytesIf(this._getStationRxBytes(t))
                    },
                    _getStationTxBytes: function(t) {
                        return t ? parseInt(r.default.getValue(this._remoteEndData, "remote.tx_bytes", 0)) : parseInt(r.default.getValue(this._remoteEndData, "stats.tx_bytes", 0))
                    },
                    _getStationRxBytes: function(t) {
                        return t ? parseInt(r.default.getValue(this._remoteEndData, "remote.rx_bytes", 0)) : parseInt(r.default.getValue(this._remoteEndData, "stats.rx_bytes", 0))
                    },
                    _getStationAverageCapacity: function() {
                        var t = r.default.getValue(this._remoteEndData, "airmax.downlink_capacity", 0),
                            e = r.default.getValue(this._remoteEndData, "airmax.uplink_capacity", 0);
                        return this.calculateIsolatedCapacity(e, t)
                    },
                    _getPollingUse: function() {
                        return r.default.getValue(this._statusData, "wireless.polling.use", 0)
                    },
                    _getAirTime: function() {
                        var t = (this._getPollingUse() / 10).toFixed(1);
                        return this.isAssociated() || (t = 0), {
                            value: t > 100 ? 100 : t,
                            textValue: t > 100 ? 100 : t + "%"
                        }
                    },
                    isFixedFrame: function() {
                        return r.default.getValue(this._statusData, "wireless.polling.fixed_frame", !1)
                    },
                    isFlexibleFrameBeta: function() {
                        return r.default.getValue(this._statusData, "wireless.polling.flex_mode", 0)
                    },
                    isTDDReporting: function() {
                        return r.default.getValue(this._statusData, "wireless.polling.ff_cap_rep", 0)
                    },
                    _getTddFraming: function() {
                        var t;
                        if (this.isFixedFrame()) {
                            var e = r.default.getValue(this._statusData, "wireless.polling.ff_frame_dur", 0);
                            t = __("Fixed") + " (" + e + "ms)" + (this.getTddFramingGpsSync() ? " & " + __("GPS Synced") : "")
                        } else t = __("Flexible" + (this.isFlexibleFrameBeta() ? " (NEW)" : " (legacy)"));
                        return {
                            value: t,
                            textValue: t
                        }
                    },
                    getTddFramingGpsSync: function() {
                        return r.default.getValue(this._statusData, "wireless.polling.gps_sync", !1)
                    },
                    _getTddFramingDlRatio: function() {
                        var t = r.default.getValue(this._statusData, "wireless.polling.ff_dl_ratio", 0);
                        return {
                            value: t,
                            textValue: t
                        }
                    },
                    _getTxRxAirtime: function() {
                        var t = r.default.getValue(this._statusData, "wireless.polling.tx_use", 0),
                            e = r.default.getValue(this._statusData, "wireless.polling.rx_use", 0);
                        return (t / 10).toFixed(1) + " / " + (e / 10).toFixed(1)
                    },
                    _getUptime: function(t) {
                        var e = r.default.getElapsedTime(t);
                        return {
                            value: e,
                            textValue: e,
                            rawValue: t
                        }
                    },
                    isWlanEnabled: function() {
                        return null != this.wlan && this.wlan.enabled
                    },
                    _getTxBytes: function() {
                        return r.default.formatBytesIf(this.wlan.status.tx_bytes)
                    },
                    _getRxBytes: function() {
                        return r.default.formatBytesIf(this.wlan.status.rx_bytes)
                    },
                    _getTxRxBytes: function() {
                        return r.default.formatBytesIf(this.wlan.status.tx_bytes) + " / " + r.default.formatBytesIf(this.wlan.status.rx_bytes)
                    },
                    isAp: function(t) {
                        return 0 === (t ? this._remoteEndData.remote.mode : this._statusData.wireless.mode).indexOf("ap")
                    },
                    isSta: function(t) {
                        return 0 === (t ? this._remoteEndData.remote.mode : this._statusData.wireless.mode).indexOf("sta")
                    },
                    isPtp: function(t) {
                        return (t ? this._remoteEndData.remote.mode : this._statusData.wireless.mode).indexOf("-ptp") > 0
                    },
                    isPtmp: function(t) {
                        return (t ? this._remoteEndData.remote.mode : this._statusData.wireless.mode).indexOf("-ptmp") > 0
                    },
                    isMixedMode: function(t) {
                        return t ? r.default.getValue(this._remoteEndData, "remote.compat_11n", 0) > 0 : r.default.getValue(this._statusData, "wireless.compat_11n", 0) > 0
                    },
                    getIeeeMode: function() {
                        var t = this._statusData.wireless.ieeemode,
                            e = this._statusData.wireless.band;
                        return "auto" === t.toLowerCase() && e > 0 && (t = 1 === e ? "11nght" : "11acvht"), t
                    },
                    _getWirelessMode: function(t) {
                        var e;
                        return this.isWlanEnabled() ? (e = this.isAp(t) ? __("AP") : __("Station"), this.isPtp(t) ? e += " " + __("PtP") : this.isPtmp(t) && this.isAp(t) ? e += " " + __("PtMP airMAX") : this.isPtmp(t) && this.isSta(t) && (e += " " + __("PtMP")), this.isMixedMode(t) ? e += " " + __("Mixed") : this.isPtmp(t) && this.isAp(t) && (e += " " + __("AC")), e) : __("Disabled")
                    },
                    _getSSID: function() {
                        var t, e;
                        t = __("SSID"), e = r.default.getValue(this._statusData, "wireless.essid", "-");
                        var a = r.default.getValue(this._statusData, "wireless.hide_essid", !1);
                        if (this.isAp() && a && (t = __("Hidden SSID")), "-" === e || "" === e) {
                            var s = i.default.repository.get("wireless:basic");
                            s && (e = s.get("ssid"))
                        }
                        return {
                            label: t,
                            value: e = _uesc(e),
                            textValue: e
                        }
                    },
                    _getWlanMac: function() {
                        return {
                            label: r.default.devname2uidevname(this.wlan.ifname) + " MAC",
                            value: this.wlan.hwaddr,
                            textValue: this.wlan.hwaddr
                        }
                    },
                    _getApMac: function() {
                        var t = this.isAssociated(),
                            e = r.default.getValue(this._statusData, "wireless.apmac", "00:00:00:00:00:00");
                        return {
                            value: t ? e : __("Not Associated"),
                            textValue: t ? e : __("Not Associated")
                        }
                    },
                    isAssociated: function() {
                        return this._getWirelessState().value == this.WirelessState.CONNECTED
                    },
                    _getSecurity: function() {
                        var t = r.default.getValue(this._statusData, "wireless.security", "-"),
                            e = t;
                        return "wep" == (t = t.toLowerCase()) ? e = "WEP" : "wpa" == t.substr(0, 3) && (e = "WPA", "2" == t.substr(3, 1) && (e += "2"), -1 != t.indexOf("aes") ? e += "-AES" : -1 != t.indexOf("tkip") && (e += "-TKIP")), __(e)
                    },
                    _getDistance: function() {
                        return this._formatDistance(r.default.getValue(this._statusData, "wireless.distance", 0))
                    },
                    _getSignal: function() {
                        var t = r.default.getValue(this._remoteEndData, "rssi", 0),
                            e = r.default.getValue(this._remoteEndData, "signal", 0);
                        return this.isAssociated() || (e = 0, t = 0), {
                            value: r.default.getPercentage(t, s.default.getRssiMax()),
                            textValue: 0 == e ? "" : e + " dBm",
                            units: "dBm"
                        }
                    },
                    _getGpsSignal: function(t) {
                        if (t) var e = r.default.getValue(this._remoteEndData, "remote.gps.fix", 0),
                            a = r.default.getValue(this._remoteEndData, "remote.gps.dop", 0);
                        else e = r.default.getValue(this._statusData, "gps.fix", 0), a = r.default.getValue(this._statusData, "gps.dop", 0);
                        var i = 0;
                        if (1 == e) {
                            var s = [
                                [20, 10],
                                [15, 20],
                                [10, 30],
                                [7, 40],
                                [5, 50],
                                [3.5, 60],
                                [2, 70],
                                [1.5, 80],
                                [1, 90],
                                [0, 100]
                            ];
                            for (var n in s)
                                if (a > s[n][0]) {
                                    i = s[n][1];
                                    break
                                }
                        }
                        return {
                            value: i,
                            textValue: 0 == i ? "" : i + " %",
                            units: "%"
                        }
                    },
                    _getGpsLocation: function(t) {
                        if (t) var e = !!r.default.getValue(this._remoteEndData, "remote.gps.fix", 0),
                            a = parseFloat(r.default.getValue(this._remoteEndData, "remote.gps.lat", 0)).toFixed(6),
                            s = parseFloat(r.default.getValue(this._remoteEndData, "remote.gps.lon", 0)).toFixed(6),
                            n = r.default.getValue(this._remoteEndData, "remote.gps.alt", 0),
                            l = r.default.getValue(this._remoteEndData, "remote.height", null);
                        else {
                            e = !!r.default.getValue(this._statusData, "gps.fix", 0), a = parseFloat(r.default.getValue(this._statusData, "gps.lat", 0).toFixed(6)), s = parseFloat(r.default.getValue(this._statusData, "gps.lon", 0).toFixed(6)), n = r.default.getValue(this._statusData, "gps.alt", 0), l = r.default.getValue(this._statusData, "host.height", null);
                            if (!e) {
                                var u = i.default.repository.get("system:location");
                                u && (a = parseFloat(u.get("latitude")), s = parseFloat(u.get("longitude")), f.default.isNaN(a) || f.default.isNaN(s) ? (a = 0, s = 0) : (a = a.toFixed(6), s = s.toFixed(6)))
                            }
                        }
                        var o = 0 != a && 0 != s,
                            _ = "- / -";
                        return o && (_ = '<a target="_blank" href=http://maps.google.com/maps?q=' + a + "," + s + ">" + a + " | " + s + "</a>"), {
                            value: _,
                            textValue: a + " / " + s + " (" + __("Alt.") + " " + Math.round(n) + " m)",
                            fix: e,
                            hasCoordinates: o,
                            lon: s,
                            lat: a,
                            alt: Math.round(n),
                            height: l
                        }
                    },
                    getGpsInfo: function(t) {
                        if (t) var e = this.getStationProperty(this.getSelectedStationMac(), this.STATION_REMOTE_GPS_LOCATION);
                        else e = this.getProperty(this.GPS_LOCATION);
                        return {
                            fix: !!e && e.get("fix"),
                            hasCoordinates: !!e && e.get("hasCoordinates"),
                            coordinates: e ? e.get("lat") + "," + e.get("lon") : "",
                            lat: e ? e.get("lat") : "",
                            lon: e ? e.get("lon") : "",
                            altitude: e ? e.get("alt") : "",
                            height: e ? e.get("height") : ""
                        }
                    },
                    _getGpsAltitude: function(t) {
                        if (t) var e = r.default.getValue(this._remoteEndData, "remote.gps.fix", 0),
                            a = r.default.getValue(this._remoteEndData, "remote.gps.alt", "-");
                        else e = r.default.getValue(this._statusData, "gps.fix", 0), a = r.default.getValue(this._statusData, "gps.alt", "-");
                        var i = "-";
                        return 1 == e && (i = Math.round(a) + " m (" + Math.round(3.2808 * a) + " ft)"), {
                            value: i,
                            textValue: i
                        }
                    },
                    _getUnmsInfo: function(t) {
                        var e = t ? this._remoteEndData.remote : this._statusData,
                            a = r.default.getValue(e, "unms.status", 0),
                            i = r.default.getValue(e, "unms.timestamp", "-"),
                            s = r.default.getValue(e, "unms.link", "https://unms.com");
                        if ("-" != i) {
                            var n = (0, h.default)(i);
                            i = n.isValid() ? n.format("YYYY-MM-DD HH:mm:ss") : "-"
                        }
                        return {
                            status: a,
                            value: i,
                            link: s = 2 != a ? "https://unms.com" : _uesc(s).replace(/^wss:\/\//, "https://").replace(/\+.*/, "")
                        }
                    },
                    isMcadReporting: function() {
                        return !1
                    },
                    _getActiveChainCount: function() {
                        var t = r.default.getValue(this._statusData, "wireless.tx_chainmask", 0);
                        return r.default.numberOfSetBits(t)
                    },
                    _getSignalPerChain: function() {
                        var t = r.default.getValue(this._remoteEndData, "rssi", 0),
                            e = r.default.getValue(this._remoteEndData, "signal", 0),
                            a = r.default.getValue(this._statusData, "wireless.rx_chainmask", 0),
                            i = r.default.getValue(this._statusData, "wireless.chanbw", null),
                            n = r.default.getValue(this._remoteEndData, "chainrssi", null),
                            l = [],
                            u = [],
                            o = e - t;
                        if (null != i && null != n)
                            for (var _ = 0; _ <= 2; _++)
                                if (a & 1 << _) {
                                    var d = r.default.rssi_to_signal(n[_], o);
                                    l.push(d), u.push(r.default.getPercentage(n[_], s.default.getRssiMax()))
                                } else l.push(0), u.push(0);
                        var c = this.isAssociated() && l.length > 1,
                            h = (c && l[0] < 0 ? l[0] + " dBm" : "-") + " / " + (c && l[1] < 0 ? l[1] + " dBm" : "-");
                        return {
                            value: h,
                            textValue: h,
                            rawValue: l,
                            chainPercentage: u
                        }
                    },
                    _getFrequency: function() {
                        if ((this.isAp() || this.isSta()) && this._getWirelessState().value != this.WirelessState.DISABLED) {
                            var t = r.default.getValue(this._statusData, "wireless.frequency", "0"),
                                e = r.default.getValue(this._statusData, "wireless.dfs", 0),
                                a = this.getChanbw(),
                                i = r.default.getValue(this._statusData, "wireless.center1_freq", "0"),
                                s = t + " [" + (i - a / 2) + " - " + (i + a / 2) + "]",
                                n = "MHz" + (0 == e ? "" : " (DFS)"),
                                l = s + " " + n;
                            return {
                                value: l,
                                textValue: l,
                                rawValue: s,
                                units: n
                            }
                        }
                        return {
                            value: "-",
                            textValue: "-",
                            rawValue: "-",
                            units: ""
                        }
                    },
                    _getFrequencyCenter1: function() {
                        var t = this.getChanbw(),
                            e = r.default.getValue(this._statusData, "wireless.center1_freq", "0");
                        return {
                            value: {
                                start: e - t / 2,
                                end: e + t / 2
                            },
                            textValue: e
                        }
                    },
                    getChanbw: function() {
                        return parseInt(r.default.getValue(this._statusData, "wireless.chanbw", 0))
                    },
                    getAntennaGain: function(t) {
                        return t ? this.getStationPropertyValue(this.getSelectedStationMac(), this.STATION_REMOTE_ANTENNA_GAIN) || 0 : parseInt(r.default.getValue(this._statusData, "wireless.antenna_gain", 0))
                    },
                    isAirBeamEnabled: function() {
                        return r.default.getValue(this._statusData, "wireless.airbeam", !1)
                    },
                    _getChannelWidth: function() {
                        var t = r.default.getValue(this._statusData, "wireless.chanbw", 0),
                            e = t;
                        this.isSta() && r.default.isChanbwAuto(t) && this._getWirelessState().value != this.WirelessState.CONNECTED && (e = i.default.device.wireless.is2GHz() || this.isPtmp() ? __("Auto") + " 20 / 40" : __("Auto") + " 20 / 40 / 80");
                        var a = 0 != e,
                            s = a ? e + " MHz" : "-";
                        return {
                            value: s,
                            textValue: s,
                            rawValue: a ? t : "-",
                            units: a ? "MHz" : "-"
                        }
                    },
                    _getNoiseFloor: function() {
                        var t = r.default.getValue(this._statusData, "wireless.noisef", 0);
                        return 0 != t && this.isAssociated() ? t + " dBm" : "-"
                    },
                    _getStationNoiseFloor: function() {
                        var t = r.default.getValue(this._remoteEndData, "noisefloor", 0);
                        return 0 != t && this.isAssociated() ? t + " dBm" : "-"
                    },
                    _getRemoteNoiseFloor: function() {
                        var t = r.default.getValue(this._remoteEndData, "remote.noisefloor", 0);
                        return 0 != t && this.isAssociated() ? t + " dBm" : "-"
                    },
                    _getTxRate: function() {
                        var t = r.default.getValue(this._statusData, "wireless.tx_idx", 0),
                            e = r.default.getValue(this._statusData, "wireless.tx_nss", 0);
                        return i.default.device.wireless.formatRate(t, e)
                    },
                    _getRxRate: function() {
                        var t = r.default.getValue(this._statusData, "wireless.rx_idx", 0),
                            e = r.default.getValue(this._statusData, "wireless.rx_nss", 0);
                        return i.default.device.wireless.formatRate(t, e)
                    },
                    _getStationSignalTxRx: function() {
                        return r.default.getValue(this._remoteEndData, "remote.signal", 0) + " / " + r.default.getValue(this._remoteEndData, "signal", 0) + " dBm"
                    },
                    getMinChainCount: function() {
                        return f.default.min([this.getStationRemoteActiveChainCount(), this.getStationActiveChainCount()])
                    },
                    getStationRemoteActiveChainCount: function(t) {
                        var e = t || this._selectedStationMac,
                            a = r.default.getValue(this._stationData.filter(function(t) {
                                return t.mac === e
                            })[0], "remote.rx_chainmask", 0);
                        return r.default.numberOfSetBits(a)
                    },
                    getStationActiveChainCount: function() {
                        var t = r.default.getValue(this._statusData, "wireless.rx_chainmask", 0);
                        return r.default.numberOfSetBits(t)
                    },
                    _atpcStatusToString: function(t) {
                        return void 0 !== s.default.ATPC_STATUS_LABEL[parseInt(t)] ? s.default.ATPC_STATUS_LABEL[parseInt(t)] : ""
                    },
                    _getTxPower: function(t) {
                        if (t) var e = r.default.getValue(this._remoteEndData, "remote.tx_power", "-"),
                            a = r.default.getValue(this._remoteEndData, "airmax.atpc_status", 0);
                        else {
                            e = r.default.getValue(this._statusData, "wireless.txpower", "-"), a = r.default.getValue(this._statusData, "wireless.polling.atpc_status", 0);
                            this.isPtmp() && this.isAp() && (a = 0)
                        }
                        var i = e + " dBm" + (a > 0 ? " (" + this._atpcStatusToString(a) + ")" : "");
                        return {
                            value: i,
                            textValue: i,
                            rawValue: parseInt(e)
                        }
                    },
                    getTxPower: function(t) {
                        return this._getTxPower(t).rawValue
                    },
                    getChainNames: function() {
                        var t = r.default.getValue(this._statusData, "chain_names", null),
                            e = "";
                        return t && t.length > 1 && (e = __("Chain") + " 0 / 1"), e
                    },
                    _getRawChainSignal: function(t) {
                        var e = r.default.getValue(this._remoteEndData, t ? "remote.rssi" : "rssi", 0),
                            a = r.default.getValue(this._remoteEndData, t ? "remote.signal" : "signal", 0);
                        if (t) var i = r.default.getValue(this._remoteEndData, "remote.rx_chainmask", 0);
                        else i = r.default.getValue(this._statusData, "wireless.rx_chainmask", 0);
                        var s = r.default.getValue(this._remoteEndData, t ? "remote.chainrssi" : "chainrssi", null),
                            n = [],
                            l = a - e;
                        if (this.getStationActiveChainCount() > 0 && null != s)
                            for (var u = 0; u <= 2; u++)
                                if (i & 1 << u) {
                                    var o = r.default.rssi_to_signal(s[u], l);
                                    n.push(0 != o ? o : "-")
                                }
                        return n
                    },
                    _getChainSignal: function(t, e) {
                        var a = this._getRawChainSignal(e),
                            i = this.isAssociated() && a.length > 1;
                        return f.default.indexOf([0, 1], t) > -1 ? i && a[t] < 0 ? a[t] + " dBm" : "-" : (i && a[0] < 0 ? a[0] + " dBm" : "-") + " / " + (i && a[1] < 0 ? a[1] + " dBm" : "-")
                    },
                    _isChainSignalDiffTooHigh: function(t, e, a) {
                        return this._getChainImbalance(t, e, a) > 5
                    },
                    _getChainImbalance: function(t, e, a) {
                        var i = parseInt(t, 10),
                            s = parseInt(e, 10);
                        return a < 2 || f.default.isNaN(i) || f.default.isNaN(s) ? 0 : Math.abs(i - s)
                    },
                    getStationRemoteChainSignal: function() {
                        var t = r.default.getValue(this._remoteEndData, "remote.rssi", 0),
                            e = r.default.getValue(this._remoteEndData, "remote.signal", 0),
                            a = r.default.getValue(this._remoteEndData, "remote.rx_chainmask", 0),
                            i = r.default.getValue(this._remoteEndData, "remote.chainrssi", null),
                            n = [],
                            l = [],
                            u = e - t;
                        if (this.getStationRemoteActiveChainCount() > 0 && null != i)
                            for (var o = 0; o <= 2; o++)
                                if (a & 1 << o) {
                                    var _ = r.default.rssi_to_signal(i[o], u);
                                    n.push(0 != _ ? _ : "-"), l.push(r.default.getPercentage(i[o], s.default.getRssiMax()))
                                } else n.push("-"), l.push(0);
                        var d = this.isAssociated() && n.length > 0,
                            c = (d && n[0] < 0 ? n[0] + " dBm" : "-") + " / " + (d && n[1] < 0 ? n[1] + " dBm" : "-");
                        return {
                            value: c,
                            textValue: c,
                            rawValue: n,
                            chainPercentage: l
                        }
                    },
                    _getAntennaCount: function() {
                        return i.default.device.wireless.getAntennaCount()
                    },
                    WirelessState: {
                        DISABLED: 0,
                        CONNECTED: 1,
                        DISCONNECTED: 2,
                        SCANNING: 3,
                        AUTHENTICATING: 4,
                        DFS_WAIT: 5
                    },
                    _getWirelessState: function() {
                        var t, e;
                        if (this.isWlanEnabled()) {
                            var a = r.default.getValue(this._statusData, "wireless.sta", []).length;
                            if (r.default.getValue(this._statusData, "wireless.cac_state", 0) > 0) t = this.WirelessState.DFS_WAIT, e = __("DFS Wait");
                            else if (a > 0) {
                                if (this.isAp()) t = this.WirelessState.CONNECTED, e = __("Connected");
                                else switch (r.default.getValue(this._statusData, "wireless.rstatus", 0)) {
                                    case s.default.RunningStatus.SCAN:
                                        t = this.WirelessState.SCANNING, e = __("Scanning") + "...";
                                        break;
                                    case s.default.RunningStatus.JOIN:
                                    case s.default.RunningStatus.AUTH:
                                    case s.default.RunningStatus.ASSOC:
                                        t = this.WirelessState.AUTHENTICATING, e = __("Authenticating") + "...";
                                        break;
                                    case s.default.RunningStatus.RUN:
                                        t = this.WirelessState.CONNECTED, e = __("Connected");
                                        break;
                                    case s.default.RunningStatus.INIT:
                                    default:
                                        t = this.WirelessState.DISCONNECTED, e = __("Disconnected")
                                }
                            } else t = this.WirelessState.DISCONNECTED, e = __("Disconnected")
                        } else t = this.WirelessState.DISABLED, e = __("Disabled");
                        return {
                            value: t,
                            textValue: e
                        }
                    },
                    _getDfsTime: function() {
                        return r.default.getValue(this._statusData, "wireless.cac_state", 0)
                    },
                    _getStationRemoteFirmware: function(t) {
                        var e = r.default.getValue(this._remoteEndData, "remote.version", "");
                        if (t) {
                            var a = e.split(".")[0];
                            return r.default.stripFirmwareVersion(e) + (a ? " (" + a + ")" : "")
                        }
                        return r.default.getFirmwareVersion(e)
                    },
                    _getStationAirtimeTx: function() {
                        return (r.default.getValue(this._remoteEndData, "airmax.tx.usage", 0) / 10).toFixed(1)
                    },
                    _getStationAirtimeRx: function() {
                        return (r.default.getValue(this._remoteEndData, "airmax.rx.usage", 0) / 10).toFixed(1)
                    },
                    _getStationAirtime: function() {
                        return this._getStationAirtimeTx() + " / " + this._getStationAirtimeRx()
                    },
                    getFirmwarePrefix: function() {
                        return UBNT.Utils.Session.get("fullVersion").split(".")[0]
                    },
                    getFirmwareVersion: function() {
                        return this.getFirmwarePrefix() + "." + r.default.getValue(this._statusData, "host.fwversion", "")
                    },
                    getDeviceName: function(t) {
                        return t ? this.getStationPropertyValue(this.getSelectedStationMac(), this.STATION_REMOTE_DEVICE_NAME) || "" : r.default.getValue(this._statusData, "host.hostname", "")
                    },
                    getDeviceModel: function(t) {
                        return t ? this.getStationPropertyValue(this.getSelectedStationMac(), this.STATION_REMOTE_DEVICE_MODEL) || "" : r.default.getValue(this._statusData, "host.devmodel", "")
                    },
                    isStationMSeries: function() {
                        return this._isMSeries(this.getStationPropertyValue(this.getSelectedStationMac(), this.STATION_REMOTE_VERSION_FULL) || "")
                    },
                    getFirmwareBuild: function() {
                        var t = /[.]([0-9]+)[.][0-9]{6}[.][0-9]{4}/.exec(UBNT.Utils.Session.get("fullVersion"));
                        return t && t[1] ? t[1] : __("Unknown")
                    },
                    _isMSeries: function(t) {
                        return -1 != t.indexOf("(XM)") || -1 != t.indexOf("(XW)") || -1 != t.indexOf("(TI)")
                    },
                    isEnabledDHCPClient: function() {
                        return 0 != r.default.getValue(this._statusData, "services.dhcpc", 0)
                    },
                    isEnabledDHCPDaemon: function() {
                        return 0 != r.default.getValue(this._statusData, "services.dhcpd", 0)
                    },
                    isEnabledDHCP6Daemon: function() {
                        return 0 != r.default.getValue(this._statusData, "services.dhcp6d_stateful", 0)
                    },
                    isEnabledPPPoE: function() {
                        return 0 != r.default.getValue(this._statusData, "services.pppoe", 0)
                    },
                    isEnabledAirview: function() {
                        return r.default.getValue(this._statusData, "services.airview", 0) > 0
                    },
                    isRunningAirview: function() {
                        return 2 == r.default.getValue(this._statusData, "services.airview", 0)
                    },
                    isEnabledServiceConfiguration: function() {
                        return 0 != r.default.getValue(this._statusData, "host.uservice", 0)
                    },
                    isPortForwardEnabled: function() {
                        return 1 == r.default.getValue(this._statusData, "portfw", 0)
                    },
                    isFirewallEnabled: function() {
                        var t = r.default.getValue(this._statusData, "firewall.iptables", 0),
                            e = r.default.getValue(this._statusData, "firewall.ebtables", 0);
                        return 1 == t || 1 == e
                    },
                    getStationData: function() {
                        return this._stationData
                    },
                    getStationCollection: function() {
                        return this._stationCollection
                    },
                    getInterfaceCollection: function() {
                        return this._interfaceCollection
                    },
                    _getDate: function(t) {
                        if (t) var e = r.default.getValue(this._remoteEndData, "remote.time", "-");
                        else e = r.default.getValue(this._statusData, "host.time", "-");
                        if ("-" != e) {
                            var a = (0, h.default)(e);
                            e = a.isValid() ? a.format("YYYY-MM-DD HH:mm:ss") : "-"
                        }
                        return e
                    },
                    getPriorityStringValue: function(t) {
                        switch (t) {
                            case s.default.AirmaxPriority.HIGH:
                                return __("High");
                            case s.default.AirmaxPriority.MEDIUM:
                                return __("Medium");
                            case s.default.AirmaxPriority.LOW:
                                return __("Low");
                            case s.default.AirmaxPriority.BASE:
                            default:
                                return __("Base")
                        }
                    },
                    getIsolatedCapacityRx: function() {
                        return r.default.getValue(this._statusData, "wireless.polling.ucap", 0)
                    },
                    getIsolatedCapacityTx: function() {
                        return r.default.getValue(this._statusData, "wireless.polling.dcap", 0)
                    },
                    _getActualPriority: function() {
                        var t = r.default.getValue(this._remoteEndData, "airmax.actual_priority", 2);
                        return this.getPriorityStringValue(t)
                    },
                    _getDesiredPriority: function() {
                        var t = r.default.getValue(this._remoteEndData, "airmax.desired_priority", 2);
                        return this.getPriorityStringValue(t)
                    },
                    _getStationRemoteSignal: function() {
                        var t = r.default.getValue(this._remoteEndData, "remote.rssi", 0),
                            e = r.default.getValue(this._remoteEndData, "remote.signal", 0);
                        return {
                            value: r.default.getPercentage(t, s.default.getRssiMax()),
                            textValue: 0 == e ? "" : e + " dBm",
                            units: "dBm"
                        }
                    },
                    _getStationSignal: function() {
                        var t = r.default.getValue(this._remoteEndData, "rssi", 0),
                            e = r.default.getValue(this._remoteEndData, "signal", 0);
                        return {
                            value: r.default.getPercentage(t, s.default.getRssiMax()),
                            textValue: 0 == e ? "" : e + " dBm",
                            units: "dBm"
                        }
                    },
                    getSelectedStationMac: function() {
                        return this._selectedStationMac
                    },
                    getSelectedStationIp: function() {
                        var t = "";
                        return this.isAssociated() ? ("0.0.0.0" !== this._selectedStationIp && (t = this._selectedStationIp), t) : t
                    },
                    getControlFrequency: function() {
                        return parseInt(r.default.getValue(this._statusData, "wireless.frequency", "0"))
                    },
                    getCenterFrequency: function() {
                        return parseInt(r.default.getValue(this._statusData, "wireless.center1_freq", "0"))
                    },
                    getUbntboxLabel: function() {
                        return this._ubntboxLabel
                    },
                    setUbntboxLabel: function(t) {
                        this._ubntboxLabel = t
                    },
                    isWatchdogReset: function() {
                        return this._isWatchdogReset
                    },
                    setIsWatchdogReset: function(t) {
                        this._isWatchdogReset = t
                    },
                    isDefaultPassword: function() {
                        return this._isDefaultPassword
                    },
                    setIsDefaultPassword: function(t) {
                        this._isDefaultPassword = t
                    },
                    isAllStationsMSeries: function() {
                        return this._isAllStationsMSeries
                    },
                    getThroughputRx: function(t) {
                        if (t) var e = i.default.chartController.options.remoteChartModel;
                        else e = i.default.chartController.options.wlanChartModel;
                        if (e) {
                            var a = e.get("data").getD3Data().rxData;
                            return a[a.length - 1]
                        }
                        return 0
                    },
                    getThroughputTx: function(t) {
                        if (t) var e = i.default.chartController.options.remoteChartModel;
                        else e = i.default.chartController.options.wlanChartModel;
                        if (e) {
                            var a = e.get("data").getD3Data().txData;
                            return a[a.length - 1]
                        }
                        return 0
                    },
                    isManagementRadioUp: function() {
                        var t = this._getInterface("ath1");
                        return null != t && t.enabled
                    },
                    isIpv6Enabled: function() {
                        var t = !1;
                        return f.default.each(this._interfaceCollection.models, function(e) {
                            e.get("status").ip6addr && (t = !0)
                        }, this), t
                    },
                    getAirCubeCollection: function() {
                        return this._airCubeCollection
                    },
                    setAirCubeCollection: function(t) {
                        for (var e in this._airCubeCollection.reset(), t)
                            if (t.hasOwnProperty(e)) {
                                var a = f.default.extend({
                                    id: t[e].hwaddr.replace(p, "")
                                }, t[e]);
                                a.fwversion = r.default.getFirmwareVersion(t[e].fwversion), this._airCubeCollection.add(a)
                            }
                        this.isRouter() && i.default.vent.trigger("status:aircube_collection_updated")
                    },
                    DEVICE_MODEL: 0,
                    DEVICE_NAME: 1,
                    FIRMWARE: 2,
                    DATE: 3,
                    NETWORK_MODE: 4,
                    CUSTOM_SCRIPTS_ENABLED: 5,
                    MEMORY_USAGE: 6,
                    CPU_USAGE: 7,
                    LAN_SPEED: 8,
                    CABLE_LENGTH: 9,
                    CABLE_SNR: 10,
                    AIRMAX_ENABLED: 11,
                    AVERAGE_CAPACITY_TX_RX: 12,
                    ISOLATED_CAPACITY_TX_RX: 13,
                    AIRTIME: 14,
                    UPTIME: 15,
                    TX_RX_BYTES: 16,
                    WIRELESS_MODE: 17,
                    SSID: 18,
                    WLAN_MAC: 19,
                    WIRELESS_STATE: 20,
                    SECURITY: 21,
                    DISTANCE: 22,
                    SIGNAL: 23,
                    SIGNAL_PER_CHAIN: 24,
                    CONNECTIONS: 25,
                    FREQUENCY: 26,
                    CHANNEL_WIDTH: 27,
                    NOISE_FLOOR: 28,
                    TX_RATE: 29,
                    RX_RATE: 30,
                    ANTENNA: 31,
                    AP_MAC: 32,
                    STATION_REMOTE_SIGNAL: 33,
                    STATION_REMOTE_SIGNAL_PER_CHAIN: 34,
                    STATION_REMOTE_TX_POWER: 35,
                    STATION_REMOTE_DEVICE_MODEL: 36,
                    STATION_REMOTE_DEVICE_NAME: 37,
                    STATION_REMOTE_FIRMWARE: 38,
                    STATION_LAST_IP: 39,
                    STATION_CONNECTION_TIME: 40,
                    STATION_DESIRED_PRIORITY: 41,
                    STATION_ACTUAL_PRIORITY: 42,
                    STATION_NOISE_FLOOR: 43,
                    STATION_ISOLATED_CAPACITY_TX_RX: 44,
                    STATION_AVERAGE_CAPACITY_TX_RX: 45,
                    STATION_AIRTIME: 46,
                    STATION_LATENCY: 47,
                    NOT_CONNECTED: 48,
                    STATION_SIGNAL_TX_RX: 49,
                    STATION_DOWNLINK_CAPACITY: 50,
                    STATION_REMOTE_TX_POWER_B: 51,
                    TX_RX_AIRTIME: 52,
                    ISOLATED_CAPACITY_TX: 53,
                    ISOLATED_CAPACITY_RX: 54,
                    TX_BYTES: 55,
                    RX_BYTES: 56,
                    STATION_MAC: 57,
                    STATION_BEAM: 58,
                    STATION_PPS: 59,
                    STATION_DISTANCE: 60,
                    STATION_TX_RATE: 61,
                    STATION_RX_RATE: 62,
                    STATION_TX_RX_BYTES: 63,
                    STATION_SIGNAL: 64,
                    STATION_SIGNAL_PER_CHAIN: 65,
                    STATION_UPLINK_CAPACITY: 66,
                    STATION_TX_RX_AIRTIME: 67,
                    DFS_WAIT_TIME: 68,
                    DISTANCE_B: 69,
                    STATION_REMOTE_SIGNAL_AP: 70,
                    STATION_REMOTE_NOISE_FLOOR: 71,
                    SIGNAL_PER_CHAIN_REMOTE: 72,
                    TX_POWER: 73,
                    STATION_ISOLATED_CAPACITY_TX_RX_PTP: 74,
                    ISOLATED_CAPACITY_TX_RX_PTP_AP: 75,
                    FREQUENCY_CENTER1: 76,
                    STATION_MAC_B: 77,
                    FCC_ID: 78,
                    PLACEHOLDER: 79,
                    SNR_LOCAL_CINR: 80,
                    SNR_LOCAL_POWER: 81,
                    SNR_REMOTE_CINR: 82,
                    SNR_REMOTE_POWER: 83,
                    PLACEHOLDER_B: 84,
                    STATION_REMOTE_VERSION_FULL: 85,
                    GPS_SIGNAL: 86,
                    GPS_LOCATION: 87,
                    STATION_SIGNAL_TX: 88,
                    STATION_SIGNAL_RX: 89,
                    STATION_SIGNAL_PER_CHAIN0: 90,
                    STATION_SIGNAL_PER_CHAIN1: 91,
                    STATION_TX_BYTES: 92,
                    STATION_RX_BYTES: 93,
                    STATION_AIRTIME_TX: 94,
                    STATION_AIRTIME_RX: 95,
                    STATION_SIGNAL_CHAIN_DIFF_TOO_HIGH: 96,
                    STATION_REMOTE_WIRELESS_MODE: 97,
                    STATION_REMOTE_DATE: 98,
                    STATION_REMOTE_MEMORY_USAGE: 99,
                    STATION_REMOTE_CPU_USAGE: 100,
                    STATION_REMOTE_NETWORK_MODE: 101,
                    STATION_REMOTE_CABLE_SNR: 102,
                    STATION_REMOTE_CABLE_LENGTH: 103,
                    STATION_REMOTE_TX_RX_BYTES: 104,
                    STATION_REMOTE_UPTIME: 105,
                    STATION_SIGNAL_PER_CHAIN_DASHBOARD: 106,
                    PLACEHOLDER_DISCONNECTED_1: 107,
                    PLACEHOLDER_DISCONNECTED_2: 108,
                    PLACEHOLDER_DISCONNECTED_3: 109,
                    PLACEHOLDER_DISCONNECTED_4: 110,
                    WLAN_DISABLED: 111,
                    MCA_STATUS: 112,
                    UPLINK_CAPACITY: 113,
                    DOWNLINK_CAPACITY: 114,
                    PROVMODE_STATUS: 115,
                    PROVMODE_TIMEOUT: 116,
                    STATION_REMOTE_DISTANCE: 117,
                    NTP_TIMESTAMP: 118,
                    TDD_FRAMING: 119,
                    TDD_FRAMING_GPS_SYNC: 120,
                    UNMS: 121,
                    PLACEHOLDER_CONNECTED: 122,
                    STATION_REMOTE_SIGNAL_CHAIN_DIFF_TOO_HIGH: 123,
                    STATION_REMOTE_LAN_SPEED: 124,
                    STATION_REMOTE_GPS_SIGNAL: 125,
                    STATION_REMOTE_GPS_LOCATION: 126,
                    STATION_SIGNAL_CHAIN_DIFF: 127,
                    STATION_REMOTE_SIGNAL_CHAIN_DIFF: 128,
                    ANTENNA_GAIN: 129,
                    STATION_REMOTE_ANTENNA_GAIN: 130,
                    DISTANCE_FROM_COORDINATES: 131,
                    TDD_FRAMING_DL_RATIO: 132,
                    GPS_ALTITUDE: 133,
                    GPS_SAT_COUNT: 134,
                    STATION_REMOTE_GPS_ALTITUDE: 135,
                    STATION_REMOTE_GPS_SAT_COUNT: 136,
                    STATION_REMOTE_TDD_FRAMING_DL_RATIO: 137,
                    STATION_REMOTE_UNMS: 138,
                    GPS_TIME_SYNC_TIMESTAMP: 139,
                    GPS_TIME_SYNC_ENABLED: 140
                }, e.default = S
            }).call(this, a(8))
        },
        572: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = Object.freeze({
                mm: {
                    ratio: {
                        metric: .001,
                        imperial: .00328084
                    },
                    system: "metric"
                },
                cm: {
                    ratio: {
                        metric: .01,
                        imperial: .0328084
                    },
                    system: "metric"
                },
                m: {
                    ratio: {
                        metric: 1,
                        imperial: 3.28084
                    },
                    system: "metric"
                },
                km: {
                    ratio: {
                        metric: 1e3,
                        imperial: 3280.84
                    },
                    system: "metric"
                },
                in : {
                    ratio: {
                        metric: 1 / 3.28084 / 12,
                        imperial: 1 / 12
                    },
                    system: "imperial"
                },
                ft: {
                    ratio: {
                        metric: 1 / 3.28084,
                        imperial: 1
                    },
                    system: "imperial"
                },
                mi: {
                    ratio: {
                        metric: 1 / 3.28084 * 5280,
                        imperial: 5280
                    },
                    system: "imperial"
                }
            });
            e.default = {
                convert: function(t, e, a) {
                    var s = i[e].system;
                    return t * i[e].ratio[s] / i[a].ratio[s]
                },
                toBest: function(t, e) {
                    var a;
                    for (var s in i)
                        if (i.hasOwnProperty(s) && i[e].system === i[s].system) {
                            var n = this.convert(t, e, s);
                            (!a || n >= 1 && n < a.value) && (a = {
                                value: n,
                                units: s
                            })
                        }
                    return a
                }
            }
        },
        581: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = r(a(38)),
                s = r(a(1074)),
                n = r(a(636)),
                l = r(a(1072)),
                u = r(a(635)),
                o = r(a(1069));

            function r(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }
            var _ = r(a(34)).default.CompositeView.extend({
                __name__: "NavigationListView",
                tagName: "div",
                childViewContainer: "ul",
                template: s.default,
                childEvents: {
                    click: "onSelect",
                    render: "onRenderChild"
                },
                getChildView: function(t) {
                    return i.default.settings.isMobileLayout() ? t.hasUrl() ? o.default : l.default : t.hasUrl() ? u.default : n.default
                },
                onSelect: function(t) {
                    this.trigger("select", t.model)
                }
            });
            e.default = _
        },
        582: function(t, e, a) {
            "use strict";
            (function(t) {
                Object.defineProperty(e, "__esModule", {
                    value: !0
                });
                var i = r(a(38)),
                    s = r(a(1075)),
                    n = r(a(637)),
                    l = r(a(581)),
                    u = r(a(9)),
                    o = r(a(34));

                function r(t) {
                    return t && t.__esModule ? t : {
                        default: t
                    }
                }
                e.default = o.default.Object.extend({
                    __name__: "NavigationController",
                    listView: l.default,
                    addItem: function(e) {
                        var a = new n.default(e);
                        if (this.list.where({
                                name: e.name
                            }).length > 0 && log.error("Duplicate menu item is added"), this.list.add(a), a.hasUrl() && this.router.route(a.get("url"), a.get("name"), t.bind(function() {
                                this.routeAction(a)
                            }, this)), a.hasKeymap()) {
                            var s = this,
                                l = function() {
                                    Mousetrap.bind(a.get("keymap"), function() {
                                        return s.onSelect(a), !1
                                    })
                                };
                            l(), i.default.listenTo(i.default.vent, "mousetrap:bind", l), i.default.listenTo(i.default.vent, "mousetrap:unbind", function() {
                                Mousetrap.unbind(a.get("keymap"))
                            })
                        }
                        return a
                    },
                    removeItem: function(t) {
                        var e = this.list.findWhere(t);
                        e && this.list.remove(e)
                    },
                    updateItem: function(t) {
                        var e = this.list.where({
                            name: t.name
                        });
                        if (e) {
                            var a = new n.default(t);
                            this.list.remove(e), this.list.add(a)
                        }
                    },
                    routeAction: function(t) {
                        this.isNavigationAllowed(t) && this.doAction(t), i.default.vent.trigger("navigate:route_action")
                    },
                    doAction: function(t) {
                        if (this.list.toggleActive(t, !0), t.get("openAction").call(t), t.hasUrl()) {
                            var e = t.get("title");
                            i.default.navigation.setDocumentTitle(e), i.default.vent.trigger("navigate:on_action", t)
                        }
                    },
                    isNavigationAllowed: function(t) {
                        var e = this.list.getActive();
                        return !e || (t && e.get("url") === t.get("url") && !!e.get("canReload") || e.get("beforeCloseAction").call(e))
                    },
                    getView: function() {
                        return this.view
                    },
                    onSelect: function(t) {
                        t.hasUrl() ? this.isNavigationAllowed(t) && (u.default.history.navigate(t.get("url"), {
                            trigger: !1
                        }), this.doAction(t)) : t.get("openAction").call(t), i.default.vent.trigger("navigate:on_select")
                    },
                    initializeView: function() {
                        return this.view = new this.listView({
                            collection: this.list
                        }), this.listenTo(this.view, "select", this.onSelect), this.view
                    },
                    initialize: function() {
                        var t = this,
                            e = u.default.Router.extend({
                                execute: function(e, a) {
                                    var i = u.default.history.fragment,
                                        s = t.list.getByUrl(i);
                                    if (s && t.isNavigationAllowed(s)) e && e.apply(this, a);
                                    else {
                                        var n = t.list.getActive();
                                        n && u.default.history.navigate(n.get("url"), {
                                            trigger: !1
                                        })
                                    }
                                }
                            });
                        this.list = new s.default, this.router = new e, this.initializeView()
                    }
                })
            }).call(this, a(3))
        },
        583: function(t, e, a) {
            "use strict";
            (function(t) {
                Object.defineProperty(e, "__esModule", {
                    value: !0
                });
                var a = {
                    disableAutocomplete: function() {
                        t(":input:not(:button)").each(function() {
                            t(this).attr("autocomplete", "off")
                        })
                    },
                    disableLastPass: function() {
                        t(":input:not(:button)").each(function() {
                            t(this).attr("data-lpignore", "true")
                        })
                    }
                };
                e.default = a
            }).call(this, a(8))
        },
        635: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = s(a(1070));

            function s(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }
            var n = s(a(34)).default.ItemView.extend({
                __name__: "NavigationLinkView",
                template: i.default,
                tagName: "div",
                className: "navigation_item",
                events: {
                    "click a": "onClick"
                },
                modelEvents: {
                    change: "render"
                },
                onClick: function(t) {
                    t.preventDefault(), this.trigger("click")
                },
                onRender: function() {
                    this.$el.find("a").toggleClass("is-item-selected", this.model.get("isActive")), this.$el.toggleClass("active", this.model.get("isActive"))
                },
                onShow: function() {
                    var t = [this.model.get("className"), this.className + "_" + this.model.get("name")];
                    this.$el.addClass(t.join(" "))
                }
            });
            e.default = n
        },
        636: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = s(a(1073));

            function s(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }
            var n = s(a(34)).default.ItemView.extend({
                __name__: "NavigationItemView",
                template: i.default,
                tagName: "li",
                className: "navigation_item",
                events: {
                    click: "onClick"
                },
                modelEvents: {
                    change: "render"
                },
                onClick: function(t) {
                    t.preventDefault(), this.trigger("click")
                },
                onRender: function() {
                    this.$el.toggleClass("is-item-selected", this.model.get("isActive")), this.$el.toggleClass("active", this.model.get("isActive"))
                },
                onShow: function() {
                    var t = [this.model.get("className"), this.className + "_" + this.model.get("name")];
                    this.$el.addClass(t.join(" "))
                }
            });
            e.default = n
        },
        637: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = function(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }(a(9)).default.Model.extend({
                __name__: "NavigationItem",
                defaults: {
                    name: "",
                    title: "",
                    icon: "",
                    url: "",
                    position: 0,
                    isActive: !1,
                    isStateful: !0,
                    canReload: !1,
                    className: "",
                    tooltip: "",
                    keymap: "",
                    openAction: function() {},
                    beforeCloseAction: function() {
                        return !0
                    }
                },
                isStateful: function() {
                    return this.get("isStateful")
                },
                hasUrl: function() {
                    return "" != this.get("url")
                },
                hasKeymap: function() {
                    return "" !== this.get("keymap")
                }
            });
            e.default = i
        },
        638: function(t, e, a) {
            "use strict";
            (function(t) {
                Object.defineProperty(e, "__esModule", {
                    value: !0
                });
                var i = u(a(38)),
                    s = u(a(34)),
                    n = u(a(583)),
                    l = u(a(3));

                function u(t) {
                    return t && t.__esModule ? t : {
                        default: t
                    }
                }
                e.default = s.default.Region.extend({
                    __name__: "DialogRegion",
                    onShow: function(e) {
                        this.view = e;
                        var a = this;
                        e.dialogOptions = e.dialogOptions || {}, this.listenTo(e, "dialog:close", this.closeDialog);
                        var i = {
                            that: this,
                            modal: !0,
                            title: "",
                            width: "auto",
                            position: {
                                my: "center",
                                at: "center",
                                of: t("body")
                            },
                            close: function() {
                                a.closeDialog()
                            },
                            open: function(e) {
                                var i = t(e.target),
                                    s = i.parent();
                                s.find(".ui-dialog-buttonset").children().removeClass("ui-button ui-widget ui-corner-all");
                                var n = setTimeout(function() {
                                    var t = i.dialog("instance");
                                    t._focusedElement && t._focusedElement.is(":disabled") && (t._focusedElement = null), t._focusTabbable(), clearTimeout(n)
                                }, 400);
                                s.hasClass("ui-draggable") && s.draggable("option", "containment", "window"), a.openDialog()
                            }
                        };
                        l.default.extend(i, l.default.result(e, "dialogOptions")), i.buttons && i.buttons.length > 0 && this.updateButtonClasses(i.buttons);
                        var s = {
                            icons: {
                                maximize: "icon-expand",
                                restore: "icon-restore"
                            }
                        };
                        l.default.extend(s, l.default.result(e, "dialogExtendOptions")), this.$el.dialog(i).dialogExtend(s), this._makeDocumentBodyOverflow("hidden"), n.default.disableAutocomplete(), n.default.disableLastPass()
                    },
                    _makeDocumentBodyOverflow: function(e) {
                        t("body").hasClass("mobile_layout") && (document.body.style.overflow = e)
                    },
                    updateButtonClasses: function(t) {
                        l.default.each(t, function(t) {
                            l.default.isUndefined(t.class) && (t.class = ""), t.class += " appMainButton appMainButton--cozy ", t.primary ? t.class += "appMainButton--primary" : t.danger && (t.class += "appMainButton--danger")
                        })
                    },
                    closeDialog: function() {
                        this.view.trigger("dialog:before_close");
                        var t = l.default.invert(i.default.openDialogs)[this.$el.selector.substr(1)];
                        t && delete i.default.openDialogs[t], this.stopListening(), this.$el && this.$el.dialog("destroy"), this._makeDocumentBodyOverflow("inherit"), this.empty(), this.mousetrap.unbind(i.default.settings.KeyboardShortcuts.ACTION_TRIGGER), this.mousetrap.unbind(i.default.settings.KeyboardShortcuts.ACTION_CANCEL)
                    },
                    openDialog: function() {
                        var t = this;
                        this.mousetrap = new Mousetrap, this.mousetrap.stopCallback = function(t) {
                            return t.target.blur(), !1
                        }, this.mousetrap.bind(i.default.settings.KeyboardShortcuts.ACTION_TRIGGER, function(e) {
                            t && t.view && t.view.onActionTrigger && l.default.isFunction(t.view.onActionTrigger) && t._triggerFocusDialogKeyboardAction(e) && t.view.onActionTrigger()
                        }), this.mousetrap.bind(i.default.settings.KeyboardShortcuts.ACTION_CANCEL, function(e) {
                            t && t.view && t.view.onActionCancel && l.default.isFunction(t.view.onActionCancel) && t._triggerFocusDialogKeyboardAction(e) && t.view.onActionCancel()
                        })
                    },
                    _isNotFocusedDialogElement: function() {
                        return !document.hasFocus() || document.activeElement.isEqualNode(document.body)
                    },
                    _isFocusedDialogPrimaryActionButton: function() {
                        if (!document.activeElement) return !1;
                        var e = t(document.activeElement);
                        return e && e.is(":button") && e.attr("primary") && "true" === e.attr("primary")
                    },
                    _triggerFocusDialogKeyboardAction: function(e) {
                        var a = document.activeElement,
                            i = a && (this.el.parentNode === a || t.contains(this.el.parentNode, a));
                        return this._isNotFocusedDialogElement() && e.target && (i = this.el.parentNode === e.target || t.contains(this.el.parentNode, e.target)), this._isFocusedDialogPrimaryActionButton() && (i = !1), i
                    }
                })
            }).call(this, a(8))
        },
        639: function(t, e, a) {
            "use strict";
            Object.defineProperty(e, "__esModule", {
                value: !0
            });
            var i = n(a(9)),
                s = n(a(3));

            function n(t) {
                return t && t.__esModule ? t : {
                    default: t
                }
            }
            var l = i.default.Model.extend({
                __name__: "PropertyModel",
                defaults: {
                    label: "",
                    toolTip: !1
                },
                initialize: function(t, e) {
                    s.default.isUndefined(t.textValue) && this.set("textValue", t.value)
                }
            });
            e.default = l
        }
    }
]);